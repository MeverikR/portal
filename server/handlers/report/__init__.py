from datetime import datetime
from dateutil.relativedelta import *
from aiohttp import web
from helpers.config import Config

from helpers.utils import DateTimeAwareEncoder, fields_preparator
from helpers.dataprovider import DataProvider
from helpers.models.params import Param
from helpers.models.users import User
from helpers.models.clients import Client
from helpers.models.groups import Group
from helpers.models.log import Statistic
from helpers.db import many, one, update, insert
from handlers.users import Users

#
from pprint import pprint

config = Config.get_config()


class Report:
    """
    Класс для отображения непосредственно самого отчета
    """

    @staticmethod
    def __encode_helper(obj):
        import json
        return json.dumps(obj, cls=DateTimeAwareEncoder)

    @staticmethod
    def __parse_incoming_date(date: str) -> datetime:
        """
        Метод помогает нам распарсить строку с датой
        :param date:
        :return:
        """
        from dateutil import parser
        dt = parser.parse(date)
        return dt

    @staticmethod
    def __extract_data(data_api_response: dict) -> list:
        if 'result' not in data_api_response:
            raise Exception('Invalid data api response - no result key')
        if 'data' not in data_api_response.get('result'):
            raise Exception('Invalid data api response - no data key')

        return data_api_response.get('result').get('data')

    async def get_list(self, request):
        """
        Получить список звонков
        :param request:
        :return:
        """
        auth = request.auth
        if request.auth.get('group') not in [1, 2]:
            return web.HTTPUnauthorized()

        # собираем все штуки для сортировки и пагинации
        limit = request.query.get('_end', '15')
        offset = request.query.get('_start', '0')
        sort = request.query.get('_sort', 'start_time')
        order = request.query.get('_order', 'DESC')
        date_from = str(request.query.get('_date_from',
                                      (datetime.now() - relativedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)))
        date_till = str(request.query.get('_date_till', datetime.now().replace(hour=23, minute=59, second=59, microsecond=0, tzinfo=None)))
        db = request.app['db']

        user = await one(db, User.get_full_by_id(auth.get('id'), auth.get('client')))
        # обновляем список тегов
        if int(auth.get('id')) > 0 and user.get('params_enable_deleted_tags_check') is True:
           u = Users()
           await u._fix_deleted_tags(auth.get('id'), request.app)

        # получаем данные текущего пользователя
        token = user['clients_token']
        # TODO: добавить фильтры из настроек юзера
        # у нас нельзя сортировать по id результат отчета, говорит prohibited
        dt = DataProvider(token)
        if sort == 'id':
            sort = 'start_time'
        try:
            dt.set_period(date_from, date_till)
        except Exception as e:
            raise web.HTTPNotAcceptable(reason='Period error. Please try again',
                                        body=str(e))


        dt.set_fields(user['params_fields'])
        if user['params_filters'] is not None and user['params_filters'] != 'null' and len(user['params_filters']) > 0:
            _flt = user['params_filters'][0].get('filters')
            for f in _flt:
                if str(f.get('value')).isdigit():
                    f['value'] = int(f['value'])

            dt.filters = user['params_filters'][0]


        dt.set_sort(
            [{'field': sort, 'order': str(order).lower()}]
        )

        if int(limit) - int(offset) > 0:
            limit = int(limit) - int(offset)
            limit = str(limit)

        try:
            calls = Report.__extract_data(await dt.get_part(limit, offset))
        except TypeError as e:

            return web.json_response(
                [],
                headers={'X-Total-Count': '0', 'X-Problem': str(e)}
            )

        except Exception as ee:
            raise web.HTTPNotAcceptable(reason=str(ee),
                                        body=str(ee))

        # calls uniq
        # calls = list({v['id']:v for v in calls}.values())
        # для снимания тега с обращения допишем в теги обращения, ибо в реакте не понятно как это сделать
        # статистика прослушанности
        static = await many(db, """
         SELECT msg FROM statistics WHERE code=30 and statistics.user_id = %s order by id ASC
         """ % auth.get('id'))
        static = [int(x.get('msg')) for x in static.get('data')]


        for call in calls:
            if int(call.get('id')) in static:
                call['listened'] = True
            else:
                call['listened'] = False

            if call.get('tags'):
                for x in call['tags']:
                    x['comm_id'] = call.get('id')


        if request.auth.get('group') == 2:
            # если пользователь, то он может видеть только теги из своего списка
            user_tags = user['params_tags']
            for call in calls:
                if call.get('tags'):
                    call['tags'][:] = [x for x in call['tags'] if x.get('tag_id') in user_tags]

        rowcount = dt.get_total()

        # статистика
        stat = {
            'user_id': request.auth.get('id'),
            'code': '20',
            'msg': 'Report fetched from:[' + str(date_from) + '] to:[' + str(date_till) + '] total:[' + str(
                rowcount) + ']'
        }
        await insert(db, Statistic.add(stat))

        return web.json_response(
            calls,
            dumps=Report.__encode_helper,
            headers={'X-Total-Count': str(rowcount)}
        )

    async def xls(self, request):
        """
        Подгружаем XLS и отдаем клиету
        :param request:
        :return:
        """
        from helpers.xls_maker import make_report

        auth = request.auth
        if request.auth.get('group') not in [1, 2]:
            return web.HTTPUnauthorized()


        date_from = str(request.query.get('_date_from',
                                      (datetime.now() - relativedelta(days=7)).replace(hour=0, minute=0, second=0, tzinfo=None)))
        date_till = str(request.query.get('_date_till', datetime.now().replace(hour=23, minute=59, second=59, tzinfo=None)))

        filters = None
        if 'filter' in request.query:

            import json
            try:
                filters = json.loads(request.query.get('filter'))
            except Exception as e:
                pass

        if filters:
            if '_date_from' in filters:
                date_from = str(filters.get('_date_from',
                                        (datetime.now() - relativedelta(days=7)).replace(hour=0, minute=0, second=0, tzinfo=None)
                                        ))

            if '_date_till' in filters:
                date_till = str(filters.get('_date_till',
                                        datetime.now().replace(hour=23, minute=59, second=59, tzinfo=None)
                                        ))



        sort = request.query.get('_sort', 'start_time')
        order = request.query.get('_order', 'DESC')

        db = request.app['db']
        user = await one(db, User.get_full_by_id(auth.get('id'), auth.get('client')))
        token = user['clients_token']
        # TODO: добавить фильтры из настроек юзера
        # у нас нельзя сортировать по id результат отчета, говорит prohibited
        dt = DataProvider(token)
        if sort == 'id':
            sort = 'start_time'

        dt.set_period(date_from, date_till)
        # различная мета инфа для отчета в XLS
        _meta = {'from': date_from, 'till': date_till,
                 'client': user['clients_name'], 'user': user['users_name'],
                 }
        dt.set_fields(user['params_fields'])
        if user['params_filters'] is not None and user['params_filters'] != 'null' and len(user['params_filters']) > 0:
            _flt = user['params_filters'][0].get('filters')
            for f in _flt:
                if str(f.get('value')).isdigit():
                    f['value'] = int(f['value'])


            print(user['params_filters'][0])
            dt.filters = user['params_filters'][0]

        dt.set_sort(
            [{'field': sort, 'order': str(order).lower()}]
        )
        report = await dt.get()

        # статистика прослушанности
        static = await many(db, """
         SELECT msg FROM statistics WHERE code=30 and statistics.user_id = %s order by id ASC
         """ % auth.get('id'))
        static = [int(x.get('msg')) for x in static.get('data')]


        for call in report.get('result').get('data'):
            if int(call.get('id')) in static:
                call['listened'] = 'Да'
            else:
                call['listened'] = 'Нет'

            if call.get('tags'):
                for x in call['tags']:
                    x['comm_id'] = call.get('id')


        if request.auth.get('group') == 2:
            # если пользователь, то он может видеть только теги из своего списка
            user_tags = user['params_tags']
            for call in report.get('result').get('data'):
                if call.get('tags'):
                    call['tags'][:] = [x for x in call['tags'] if x.get('tag_id') in user_tags]

        xls_filec = make_report(report,
                                fields_preparator(config.get('app').get('fields_avaliable')),
                                user['params_fields'], _meta, {
                                    'hide_sys_id' : user['params_hide_sys_id'],
                                    'hide_sys_aon' : user['params_hide_sys_aon'],
                                    'hide_sys_player' : user['params_hide_sys_player'],
                                    'hide_sys_static' : user['params_hide_sys_static'],
                                })

        return web.Response(
            body=xls_filec,
            headers={
                "Сontent-disposition": "attachment; filename=report.xls",
                "Content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet; base64",
                #                    "Content-Length" : str(len(xls_filec)),
                "Content-Transfer-Encoding": "binary",
                "Cache-Control": "must-revalidate",
                "Pragma": "public"
            }
        )

    async def get_one(self, request):
        """
        :param request:
        :return:
        """
        auth = request.auth
        if auth.get('group') not in [1, 2]:
            return web.HTTPUnauthorized()

        id = request.match_info.get('id') or request.get('id') or 0

        return web.json_response({'success': True})
