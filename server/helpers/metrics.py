import logging
from logging import config as logger_config

class Metrics:
    """
    Класс для работы с метриками
    В конструкторе необходимо передать объект кеша
    Ибо часть метрик храниться в редисе
    И нужно еще и БД
    """

    def __init__(self, app, config):
        self.cache = app.get('cache')
        self.db = app.get('db')
        logger_config.dictConfig(config.get('logging'))
        logger = logging.getLogger()
        self.logger = logger
        #self.pref = config.get('metrics').get('default_prefix') or ''
        # список доступных метрик
        self.available = ['jwt_issued_count', 'crash_500', 'data_api_failed_request_count', 'data_api_added_tag_count',
                          'listened_call_count'
                          ]



    async def renew(self, app = None):
        """
        Очищаем все метрики и начинаем снова
        Это выполняется один раз при запуске приложения
        :return:
        """

        for x in self.available:
            await self.cache.set_cache_wo_expire(str(x).strip(), str(0))


    async def inc(self, name):
        """
        Увеличить счетчик метрики
        :param name:
        :return:
        """
        if name not in self.available:
            return 0

        param = await self.cache.get_cache(str(name).strip())
        if not param:
            param = 0
        param = int(param)
        param += 1
        self.logger.debug('Metric %s incremented' % name)
        await self.cache.set_cache_wo_expire(str(name).strip(), str(param))
        return param

    async def get(self, name):
        """
        Получить метрику
        :param name:
        :return:
        """
        if name not in self.available:
            return 0
        self.logger.debug('Metric %s fetched' % name)

        return await self.cache.get_cache(str(name).strip() or 0)


    async def all(self):
        """
        Вернуть все метрики в виде словарика :)
        :return:
        """
        self.logger.debug('All Metric fetched')
        ret = {}
        for x in self.available:
            name = str(x).strip()
            ret[name] = int(await self.cache.get_cache(name) or 0)
        return ret