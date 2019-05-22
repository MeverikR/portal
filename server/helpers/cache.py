# -*- coding: utf-8 -*-
from aiocache import caches
__all__ = ('MicroCacher', )

class MicroCacher:
    """
    Простой класс для управления кешем
    """

    def __init__(self, cache_conf: dict):
        self.mc  = caches
        self.expire = 3600
        self.logger = None
        self.mc.set_config({
            'default' : {
            'cache': "aiocache.RedisCache",
            'endpoint': cache_conf['host'],
            'port': cache_conf['port'],
            'timeout': int(cache_conf['timeout']),
            'namespace': str(cache_conf['namespace']),
            'serializer': {
                'class': "aiocache.serializers.PickleSerializer"
            }
        }})

        self.cache = self.mc.get('default')


    def set_logger(self, logger):
        self.logger = logger

    async def test(self, app = None):
        """
        Пинг сервера
        :return:
        """
        import time
        res = await self.cache.raw('info', 'server')
        if self.logger:
            self.logger.info('MicroCache loader test: %s' % str(res ))
        await self.set_cache_wo_expire('startup_time', time.time())
        return res



    async def set_cache(self, key, val):
        if self.logger:
            self.logger.info('MicroCache: set_cache %s' % key)
        return await self.cache.set(key, val, self.expire)

    async def set_cache_wo_expire(self, key, val):
        if self.logger:
            self.logger.info('MicroCache: set_cache %s' % key)
        return await self.cache.set(key, val)


    async def is_exists(self, key):
        if self.logger:
            self.logger.info('MicroCache: is_exists %s' % key)
        return await self.cache.exists(key)

    async def get_cache(self, key):
        if self.logger:
            self.logger.info('MicroCache: get_cache %s' % key)
        return await self.cache.get(key)

    async def kill_cache(self, key):
        if self.logger:
            self.logger.info('MicroCache: kill_cache %s' % key)
        return await self.cache.delete(key)

    async def expire_cache(self, key, ttl):
        if self.logger:
            self.logger.info('MicroCache: expire_cache %s ttl: %s' % (key, ttl))
        return await self.cache.expire(key, ttl)

    def set_expire(self, ttl):
        if self.logger:
            self.logger.info('MicroCache: set_expire DEFAULT %s ' % (ttl))
        self.expire = ttl
        return True    




