from aiohttp import web
import time
from datetime import datetime
from aiohttp_cors import CorsViewMixin



class CheckHealth(web.View, CorsViewMixin):

    async def __print_response(self):

        metrics = self.request.app.get('metrics')

        return web.json_response(await metrics.all())

    async def get(self):
       return await self.__print_response()
    async def post(self):
        return await  self.__print_response()
    async def put(self):
        return await self.__print_response()

