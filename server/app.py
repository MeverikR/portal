import logging
from logging import config as logger_config

from aiohttp import web
#
from handlers.check_health import CheckHealth
from handlers.main import Main
from handlers.users import Users
from handlers.clients import Clients
from handlers.report import Report
from handlers.statistics import Statistics
from helpers.config import Config
from helpers.cors import allow_cors
from helpers.middlewares import error_middleware, auth_middleware
from helpers.mail import Mail
from helpers.db import init_pg, close_pg
from helpers.metrics import Metrics


try:
    # грузим конфиг
    config = Config.get_config()
    # грузим логгер
    logger_config.dictConfig(config.get('logging'))
    logger = logging.getLogger()
    # грузим почтовку
    mail = Mail(**config['mail'])

    # грузим дефолтные мидлвари
    MIDDLEWARE = [error_middleware, auth_middleware]
    # подгрузка настроек отпраки email-ов при ошибках
    if 'error_mailing' in config:
        mail.init_error_mailer(**config['error_mailing'])


except Exception as e:
    print(f'Cant start server during config problems: {str(e)}')
    exit()


def main():
    try:
        app_name = config.get('app').get('name')
        app_ver = config.get('app').get('ver')
        logger.info(f'Welcome to {app_name} [{app_ver}] !')

        # Если в конфиге кто-то включил нормолизатор роутов
        if config.get('app').get('normalize_path'):
            from aiohttp.web import normalize_path_middleware
            MIDDLEWARE.append(normalize_path_middleware())
            logger.info('Path normalized loaded to routes!')

        app = web.Application(middlewares=MIDDLEWARE)

        # Redis в данном приложении нужен полюбому!
        # мы будем хранить в нем сесси и входы юзеров
        if config.get('redis'):
            if config.get('redis').get('host') and config.get('redis').get('port'):
                logger.info('Path normalized loaded to routes!')
                from helpers.cache import MicroCacher
                microcache = MicroCacher(config.get('redis'))
                microcache.set_logger(logger)

                # по традиции добавляем кеш в глобальный объект приложения - это очень удобно!
                app['cache'] = microcache

        else:
            raise Exception('This application require redis in config. Please set redis host/port/other and restart application')

        # это из-за Cors, иначе можно было бы заюзать add_view
        app.router.add_route('*', '/check_health/', CheckHealth)

        main = Main()
        # роуты зашлушки
        app.router.add_route('GET', '/', main.index)
        app.router.add_route('POST', '/', main.index_post)
        app.router.add_route('GET', '/ws', main.websocket_handler)
        # роут входа - получаем токен для клиента и инфу о юзере
        # логаут не нужен. Клиент просто грохает токен
        app.router.add_route('POST', '/login', main.login)
        app.router.add_route('GET', '/logout', main.logout)

        # статистика
        stat = Statistics()
        app.router.add_route('GET', '/dashboard/{id}', stat.dash)
        app.router.add_route('GET', '/listen', stat.listen)

        # маршруты пользователей
        users = Users()
        app.router.add_route('GET', '/users', users.get_list)
        app.router.add_route('GET', '/users/{id}', users.get_one)
        app.router.add_route('PUT', '/users/{id}', users.update)
        app.router.add_route('POST', '/users', users.create)
        app.router.add_route('DELETE', '/users/{id}', users.delete)


        # маршруты клиентов
        clients = Clients()
        app.router.add_route('GET', '/clients', clients.get_list)
        app.router.add_route('GET', '/clients/{id}', clients.get_one)
        app.router.add_route('PUT', '/clients/{id}', clients.update)
        app.router.add_route('POST', '/clients', clients.create)
        app.router.add_route('DELETE', '/clients/{id}', clients.delete)
        # возможность добавлять клиенту теги
        app.router.add_route('GET', '/tags', clients.get_tags)
        app.router.add_route('POST', '/tags', clients.create_tag)
        app.router.add_route('POST', '/set_tag', clients.set_tag)
        app.router.add_route('POST', '/unset_tag', clients.unset_tag)



        # маршруты для самого отчета
        reports = Report()
        app.router.add_route('GET', '/reports', reports.get_list)
        app.router.add_route('GET', '/reports/{id}', reports.get_one)
        app.router.add_route('GET', '/xls', reports.xls)

        app['metrics'] = Metrics(app, config)
        app['websockets'] = {}
        app['_log'] = logger

        app.on_startup.append(init_pg)
        app.on_startup.append(microcache.test)
        app.on_startup.append(app['metrics'].renew)
        logger.debug('Metrics has been flushed, starting from zero')
        app.on_cleanup.append(close_pg)
        if config.get('cors'):
            allow_cors(app)
        web.run_app(app, host=config.get('host'), port=config.get('port'))
    except Exception as e:
        mail.send_error(str(e))
        print(f'Cant start server during startup error: {str(e)}')
        exit()

if __name__ == '__main__':
    main()