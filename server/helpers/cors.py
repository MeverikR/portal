import aiohttp_cors
import logging
from helpers.config import Config
config = Config.get_config()
logger = logging.getLogger()


def allow_cors(app):
    cors = aiohttp_cors.setup(app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_methods="*",
                allow_headers="*",
                max_age=3600
            )
        })

    for route in list(app.router.routes()):
        logger.info(f'Adding cors to {route.method} {route.handler}')
        cors.add(route)
