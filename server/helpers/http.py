import aiohttp

from helpers.cache import MicroCacher
from helpers.config import Config
config = Config.get_config()
microcache = MicroCacher(config.get('redis'))


class Http:
    """
    Класс релизует простую обертку для клментской сессии
    Используется в различных клиентах
    """

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *err):
        await self._session.close()
        self._session = None

    async def fetch(self, url):
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            return await resp.read()

    async def post_json(self, url, json: dict):
        """
        Отправить по http запрос POST с телом JSON
        И получить в обработчку также JSON.
        А вот если он получит не JSON, то бросит ошибочку.
        :param url: - урл посылки
        :param json: - словарь НЕ СТРОКА!
        :return:
        """
        #pref = config.get('metrics').get('default_prefix') or 'prod.custom_comagic.listen_portal'
        #metrica = int(await microcache.get_cache('data_api.requests') or 0)
        #if not metrica:
        #    metrica = 0
        #metrica += 1
        #await microcache.set_cache_wo_expire('data_api.requests', str(metrica))

        async with self._session.post(url, json=json) as resp:
            resp.raise_for_status()
            return await resp.json()

