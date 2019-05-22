import aiohttp
import asyncio
from helpers.http import Http
from datetime import *
from dateutil.relativedelta import *
import dateutil.parser as date_parser
import uuid  # для генерации id запроса

from helpers.cache import MicroCacher
from helpers.config import Config
config = Config.get_config()
microcache = MicroCacher(config.get('redis'))

## dev dependencies
import pprint

NOW = datetime.now()
MAX_PERIOD_DAYS = 90  # ограничение CM
DEF_DT_FORMAT = '%Y-%m-%d %H:%M:%S'
MAX_COMAGIC_ROWS = 10000
MAX_QUERIES_AT_ONCE = 5
POINTS_TO_CHILL = 15  # если осталось <= этим балам, то запускаем восстановление балов через ожидание
REQUIRED_FIELDS = ['id', 'communication_id', 'tags',
         'call_records', 'is_lost', 'contact_phone_number']

class DataProvider:
    """
    Модель для операций над звонками
    через Data API CoMagic
    """

    def __init__(self, token: str, default_period_days: int = 1, base_url: str = 'https://dataapi.uiscom.ru/v2.0'):

        if not token:
            raise Exception('Can`t create instance of comagic calls data provider without user token')
        self.token = token
        self.base_url = base_url
        self._last_prepared_query = None  # просто для отладки
        self._last_query_total = 0
        self.filters = None
        self.sort = None
        # по умолчанию используем период в 1 день :)
        self.period = {
            'from': (NOW - relativedelta(days=default_period_days)).replace(hour=0, minute=0, second=0, microsecond=0),
            'till': NOW.replace(hour=23, minute=59, second=59, microsecond=59)
        }
        # список полей для запроса по умолчанию.
        # По большому счету они один хрен у всех одинаковые,
        # только что-то скрыть могут захотеть

        self.fields = REQUIRED_FIELDS

    def __update_query_id(self) -> str:
        return str(uuid.uuid1())

    def __pairwise(self, iterable):
        import itertools
        "s -> (s0,s1), (s1,s2), (s2, s3), ..."
        a, b = itertools.tee(iterable)
        next(b, None)
        return zip(a, b)

    def get_dates_list(self, start_date, end_date, increment, period):
        """
        Генерирует список дат между двумя датами по заданному интервалу
        :param start_date:
        :param end_date:
        :param increment:
        :param period:
        :return:
        """
        result = []
        nxt = start_date
        delta = relativedelta(**{period: increment})
        while nxt <= end_date:
            result.append(nxt)
            nxt += delta
        return result

    def __get_chunks(self, lst: list, in_parts: int) -> list:
        """
        Разбить список на кусочки и вернуть список с ними
        :param lst:
        :param in_parts: - элементов в куске
        :return:
        """
        for _i in range(0, len(lst), in_parts):
            yield lst[_i:_i + in_parts]

    def __get_period(self):
        return self.period

    def get_last_prepared_query(self):
        return self._last_prepared_query

    def get_formated_period(self):
        period = self.__get_period()
        return {
            'date_from': period.get('from').strftime(DEF_DT_FORMAT),
            'date_till': period.get('till').strftime(DEF_DT_FORMAT)
        }

    async def __validate_answer(self, response):
        """
        Валидация ответа из CoMagic
        Ловим различные возможные ошибки
        :return:
        """
        if not response:
            raise Exception('Can`t perform query to Comagic DATA API. Some errors found. Try later or check token.')
        if len(response) != 1:
            raise Exception('Comagic RPC response error. More than one response data found. ')
        response = response[0]
        if 'error' in response:
            # добавим учет ошибок при запросах к дата апи
            #pref = config.get('metrics').get('default_prefix') or 'prod.custom_comagic.listen_portal'
            metrica = int(await microcache.get_cache('data_api_failed_request_count') or 0)
            if not metrica:
                metrica = 0
            metrica += 1
            await microcache.set_cache_wo_expire('data_api_failed_request_count', str(metrica))

            raise Exception('Can`t perform query to Comagic DATA API: %s [%s]' %
                            (response.get('error').get('message'), response.get('error').get('data').get('mnemonic')))
        if 'result' not in response:
            raise Exception('Comagic RPC response error. No Result property')

        if 'total_items' not in response.get('result').get('metadata'):
            raise Exception('Comagic RPC response error. No Total property. Can`t detect how many records we get.')

        self._last_query_total = int(response.get('result').get('metadata').get('total_items'))

        return response


    def __prepare_request(self, limit: int = MAX_COMAGIC_ROWS, offset: int = 0, period: dict = None):

        if limit:
            _limit = limit
        else:
            _limit = MAX_COMAGIC_ROWS  # это максимум для одного запроса
        if offset:
            _offset = offset
        else:
            _offset = 0  # начинаем с 1й

        data_url = self.base_url
        if period:
            date_from = period.get('from')
            date_till = period.get('till')
        else:
            _prd = self.__get_period()
            date_from = _prd.get('from')
            date_till = _prd.get('till')

        params = {
            'access_token': str(self.token),
            'date_from': date_from.strftime(DEF_DT_FORMAT),
            'date_till': date_till.strftime(DEF_DT_FORMAT),
            'limit': int(_limit),
            'offset': int(_offset),
            # TODO: фильтр и сортировка
            'fields': self.fields
        }

        if self.filters and len(self.filters) > 0:
            params['filter'] = self.filters

        if self.sort and len(self.sort) > 0:
            params['sort'] = self.sort

        rpc = {
            'jsonrpc': '2.0',
            'id': self.__update_query_id(),
            'method': 'get.calls_report',
            'params': params
        }

        ret = {'url': data_url, 'json': rpc}
        self._last_prepared_query = ret
        print(ret )

        return ret

    def get_total(self):
        return int(self._last_query_total)

    def set_part(self, limit: int, offset:int) -> bool:
        if not limit or not offset:
            return False
        self.part = {'limit' : limit, 'offset' : offset}
        return True

    def set_fields(self, fields : list):
        self.fields = REQUIRED_FIELDS + fields
        return self.fields

    def get_fields(self):
        return self.fields

    def set_sort(self, sorter: list) -> bool:
        """
        Добавляем сортировку
        :param sorter:
        :return:
        """
        if not any('field' in d for d in sorter):
            return False
        if not any('order' in d for d in sorter):
            return False
        self.sort = sorter
        return True


    def get_filters(self):
        return self.filters

    def set_filter(self, filters: list, condition: str) -> bool:
        """
        Устанавливаем фильтрацию запроса
        :param filters: - должен быть списком словарей
        :return:
        """
        if not any('value' in d for d in filters):
            return False
        if not any('field' in d for d in filters):
            return False
        if not any('operator' in d for d in filters):
            return False

        self.filters = {'filters' : filters, 'condition' : condition}
        return True




    def set_period(self, _from, _till) -> bool:
        """
        Установить период выборки
        :param _from:  - дата с
        :param _till:  - дата по
        :return:
        """
        if not _from or not _till:
            raise Exception('Can`t set period - empty data passed')

        # если передан не объект а строка
        if isinstance(_from, str):
            # превращаем строку в объект datetime
            # TODO: возможно тут словить ошибку и вернуть период по уму
            _from = date_parser.parse(_from).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

        if isinstance(_till, str):
            # превращаем строку в объект datetime
            # TODO: возможно тут словить ошибку и вернуть период по уму
            _till = date_parser.parse(_till).replace(hour=23, minute=59, second=59, microsecond=0,  tzinfo=None)

        if _from > _till:
            # ибо нельзя, чтоб дата начала была меньше даты окончания
            return False

        self.period = {'from': _from, 'till': _till}

        return True

    async def set_tag_communication(self, communication_id, tag_id, communication_type='call' ):
        """
        Установить тег на обращение
        :param communication_id:
        :param tag_id:
        :param communication_type:
        :return:
        """
        params = {
            'access_token': str(self.token),
            'communication_id': int(communication_id),
            'communication_type' : str(communication_type),
            'tag_id' : int(tag_id)
        }
        rpc = {
            'jsonrpc': '2.0',
            'id': self.__update_query_id(),
            'method': 'set.tag_communications',
            'params': params
        }
        data_url = self.base_url
        request_payload = {'url': data_url, 'json': rpc}
        self._last_prepared_query = request_payload
        async with Http() as http:
            response = await asyncio.gather(
                http.post_json(
                    **(request_payload )
            ))

        return response[0]


    async def unset_tag_communication(self, communication_id, tag_id, communication_type='call' ):
        """
        Установить тег на обращение
        :param communication_id:
        :param tag_id:
        :param communication_type:
        :return:
        """
        params = {
            'access_token': str(self.token),
            'communication_id': int(communication_id),
            'communication_type' : str(communication_type),
            'tag_id' : int(tag_id)
        }
        rpc = {
            'jsonrpc': '2.0',
            'id': self.__update_query_id(),
            'method': 'unset.tag_communications',
            'params': params
        }
        data_url = self.base_url
        request_payload = {'url': data_url, 'json': rpc}
        self._last_prepared_query = request_payload
        async with Http() as http:
            response = await asyncio.gather(
                http.post_json(
                    **(request_payload )
            ))

        return response[0]


    async def get_part(self, limit: int = MAX_COMAGIC_ROWS, offset: int = 0):
        """
        Получить часть отчета оч. быстро
        :return:
        """
        _period = self.__get_period()
        if 'from' not in _period or 'till' not in _period:
            return False

        if not limit:
            return False


        _from = _period.get('from')
        _till = _period.get('till')
        _period_diff = _till - _from

        if _period_diff.days >= 90:
            raise Exception('90 days limit reached')

        async with Http() as http:
            first_request = await asyncio.gather(
                http.post_json(**(self.__prepare_request(limit=limit, offset=offset)))
            )

        first_request = await self.__validate_answer(first_request)
        _meta = first_request['result']['metadata']
        _total = self.get_total()
        if not _total or _total <= 0:
            return False

        return first_request


    # def get_fields(self):
    #     """
    #     Вернуть все поля
    #     """
    #     # убираем поля с которыми не надо баловаться
    #     fields = self.fields.copy()
    #     return [x for x in fields if x not in REQUIRED_FIELDS]

    async def add_tag(self, name):
        """
        Создать новый тег в ЛК
        """
        params = {
            'access_token': str(self.token),
            'name': str(name)
        }
        rpc = {
            'jsonrpc': '2.0',
            'id': self.__update_query_id(),
            'method': 'create.tags',
            'params': params
        }
        data_url = self.base_url
        request_payload = {'url': data_url, 'json': rpc}
        self._last_prepared_query = request_payload
        async with Http() as http:
            response = await asyncio.gather(
                http.post_json(
                    **(request_payload )
            ))

        return response[0]


    async def get_tags(self, limit_ = None, offset_ = None, search_ = None):
        """
        Получить список всех тегов клиента из Data API
        :return:
        """
        params = {
            'access_token': str(self.token)
        }

        if self.sort and len(self.sort) > 0:
            params['sort'] = self.sort

        if limit_ and offset_:
            params['limit'] = int(limit_)
            params['offset'] = int(offset_)
        if search_:
            if self.filters and self.filters.get('filters'):
                self.filters['filters'].append( {'field' : 'name', 'operator': 'like', 'value': '%' + str(search_) + '%'})
            else:
                self.filters = {}
                self.filters['filters'] = [{'field' : 'name', 'operator': 'like', 'value': '%'+ str(search_) + '%'}]
                self.filters['condition'] = 'and'

        if self.filters and self.filters.get('filters'):
            params['filter'] = self.filters

        rpc = {
            'jsonrpc': '2.0',
            'id': self.__update_query_id(),
            'method': 'get.tags',
            'params': params
        }
        data_url = self.base_url
        request_payload = {'url': data_url, 'json': rpc}
        self._last_prepared_query = request_payload
        async with Http() as http:
            response = await asyncio.gather(
                http.post_json(
                    **(request_payload )
            ))

        response  = await self.__validate_answer(response)
        _meta = response['result']['metadata']
        data = response['result']['data']
        self._last_query_total = _meta.get('total')

        if limit_ and offset_:
            return {'data' : data, 'total' : str(_meta.get('total_items'))}
        return data



    async def get(self):
        """
        Получить много данных, вообще все
        Метод используется для генерации XLS
        и возвращает ответ
        :return:
        """

        _period = self.__get_period()

        if 'from' not in _period or 'till' not in _period:
            return False

        _from = _period.get('from')
        _till = _period.get('till')
        _period_diff = _till - _from

        if _period_diff.days >= 90:
            _VSE = []

            # обработка более 90 дней
            date_list = self.get_dates_list(_from, _till, 1, 'months')
            date_list_pairs = list(self.__pairwise(date_list))
            for period_part in date_list_pairs:
                pprint.pprint('Woriking period from %s to %s ' % period_part)
                async with Http() as http:
                    first_request = await asyncio.gather(
                        http.post_json(
                            **(self.__prepare_request(period={'from': period_part[0], 'till': period_part[1]})))
                    )

                # считаем тотал
                first_request = await self.__validate_answer(first_request)
                _meta = first_request['result']['metadata']
                _total = self.get_total()
                pprint.pprint('Total for period %s ' % _total)

                if not _total or _total <= 0:
                    return False

                if self._last_query_total > MAX_COMAGIC_ROWS:
                    pprint.pprint('Going into cycle because %s -> %s ' % (self._last_query_total, MAX_COMAGIC_ROWS))
                    # делаем цикл по остаткам
                    import math
                    _iterations = math.ceil(_total / MAX_COMAGIC_ROWS)
                    pprint.pprint('Iterations: %s' % _iterations)
                    _query_pool = []

                    for i in range(1, _iterations):
                        _offset = MAX_COMAGIC_ROWS * i
                        _limit = MAX_COMAGIC_ROWS
                        # просто подготавливаем запросы пока еще ничего не корутинитсо
                        _query_pool.append(self.__prepare_request(_limit, _offset))

                    # эта штука бахает сразу пачку запросов из кверипула нашего
                    if int(_iterations) <= int(MAX_QUERIES_AT_ONCE):
                        async with Http() as http:
                            all = await asyncio.gather(*[
                                asyncio.ensure_future(http.post_json(**query))
                                for query in _query_pool
                            ])
                    else:
                        # нам надо сделать слипы после каждых n запросов
                        _chunks = list(self.__get_chunks(_query_pool, MAX_QUERIES_AT_ONCE))
                        all = []
                        for _part in _chunks:
                            async with Http() as http:
                                all += await asyncio.gather(*[
                                    asyncio.ensure_future(http.post_json(**query))
                                    for query in _part
                                ])
                            _last_resp = all[-1:]
                            _last_resp = await self.__validate_answer(_last_resp)
                            _meta = _last_resp.get('result').get('metadata')
                            minutes_remaining = int(_meta.get('limits').get('minute_remaining'))
                            minutes_reset = int(_meta.get('limits').get('minute_reset'))
                            if minutes_remaining <= POINTS_TO_CHILL:
                                await asyncio.sleep(minutes_reset)

                    for resp in all:
                        resp = await self.__validate_answer([resp])
                        first_request['result']['data'] = first_request['result']['data'] + resp['result']['data']

                    _VSE.append(first_request)  # тут все в куче

                else:
                    # если все уместилось возвращаем ответ
                    _VSE.append(first_request)

                _last_resp = _VSE[-1:][-1:]
                _last_resp = await self.__validate_answer(_last_resp)
                _meta = _last_resp.get('result').get('metadata')
                minutes_remaining = int(_meta.get('limits').get('minute_remaining'))
                minutes_reset = int(_meta.get('limits').get('minute_reset'))
                if minutes_remaining <= POINTS_TO_CHILL:
                    await asyncio.sleep(minutes_reset)


            ret = _VSE.pop(0)
            super_total = ret.get('result').get('metadata').get('total_items')
            for resp in _VSE:
                resp = await self.__validate_answer([resp])
                super_total += self.get_total()
                ret['result']['data'] = ret['result']['data'] + resp['result']['data']
                self._last_query_total = super_total

            return ret


        else:
            # обычный запрос без цикла по периодам
            # делаем один сперва обычный синхронный запрос и получаем тотал
            async with Http() as http:
                first_request = await asyncio.gather(
                    http.post_json(**(self.__prepare_request()))
                )
            # первый запрос выполнился, проверяем что там нет ошибки
            first_request = await self.__validate_answer(first_request)
            _meta = first_request['result']['metadata']
            _total = self.get_total()
            if not _total or _total <= 0:
                return False

            if self._last_query_total > MAX_COMAGIC_ROWS:
                # делаем цикл по остаткам
                import math
                _iterations = math.ceil(_total / MAX_COMAGIC_ROWS)
                _query_pool = []

                for i in range(1, _iterations):
                    _offset = MAX_COMAGIC_ROWS * i
                    _limit = MAX_COMAGIC_ROWS
                    # просто подготавливаем запросы пока еще ничего не корутинитсо
                    _query_pool.append(self.__prepare_request(_limit, _offset))

                # эта штука бахает сразу пачку запросов из кверипула нашего
                if int(_iterations) <= int(MAX_QUERIES_AT_ONCE):
                    async with Http() as http:
                        all = await asyncio.gather(*[
                            asyncio.ensure_future(http.post_json(**query))
                            for query in _query_pool
                        ])
                else:
                    # нам надо сделать слипы после каждых n запросов
                    _chunks = list(self.__get_chunks(_query_pool, MAX_QUERIES_AT_ONCE))
                    all = []
                    for _part in _chunks:
                        async with Http() as http:
                            all += await asyncio.gather(*[
                                asyncio.ensure_future(http.post_json(**query))
                                for query in _part
                            ])
                        _last_resp = all[-1:]
                        _last_resp = await self.__validate_answer(_last_resp)
                        _meta = _last_resp.get('result').get('metadata')
                        minutes_remaining = int(_meta.get('limits').get('minute_remaining'))
                        minutes_reset = int(_meta.get('limits').get('minute_reset'))
                        if minutes_remaining <= POINTS_TO_CHILL:
                            await asyncio.sleep(minutes_reset)

                for resp in all:
                    resp = await self.__validate_answer([resp])
                    first_request['result']['data'] = first_request['result']['data'] + resp['result']['data']

                return first_request  # тут все в куче

            else:
                # если все уместилось возвращаем ответ
                return first_request
