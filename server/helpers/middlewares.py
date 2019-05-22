"""
Здесь опишем все мидлвари
"""
import re, jwt
from aiohttp import web
from helpers.config import Config
from handlers.main import Main


config = Config.get_config()

JWT_EXP_DELTA_SECONDS =int(config.get('app').get('security').get('jwt_expire_seconds'))
JWT_SECRET = str(config.get('app').get('security').get('jwt_secret'))
JWT_ALGORITHM = str(config.get('app').get('security').get('jwt_algorithm'))

WHITE_LIST_ROUTES = [r'/login', r'/check_health', r'/bad_route', r'/ws']

def check_request(request, entries):
    """
    Метод проверки маршрута, нужен для авторизации
    :param request:
    :param entries:
    :return:
    """
    for pattern in entries:
        if re.match(pattern, request.path):
            return True

    return False

# мидлварь для авторизации
@web.middleware
async def auth_middleware(request, handler):
    """
    Проверяем токен в каждом запросе
    :param request:
    :param handler:
    :return:
    """
    metrics = request.app.get('metrics')
    await metrics.inc('requests')
    # в каждый реквест будем добавлять поле auth

    request.auth = None
    if check_request(request, WHITE_LIST_ROUTES): # если белый роут, пропускаем без токена
        return await handler(request)
    if request.method == 'OPTIONS':
        return await handler(request)


    # дергаем из заголовка авторизацию
    if 'Authorization' not in request.headers:
        raise web.HTTPForbidden(
            reason='Please login first',
        )


    try:
        scheme, jwt_token = request.headers.get(
            'Authorization'
        ).strip().split(' ')
    except ValueError:
        raise web.HTTPForbidden(
            reason='Please login first',
        )


    if not jwt_token:
        msg = 'Please login!'
        return web.HTTPUnauthorized(reason=msg , body=msg )

    try:
        jwt_token = jwt_token.strip('"').strip("'")
        # так как подделать payload не могут, вся инфа у нас уже будет внутри, в БД за данными юзера ходить не надо
        request.auth = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        # проверим, что токен выдан нами :)
        cache = request.app.get('cache')
        token_from_redis = await cache.get_cache('uid_token_' + str(request.auth.get('id'))) or []

        if jwt_token not in token_from_redis:
            # если в редисе нет нашего токена, значит надо обновить юзеру профиль
            #TODO: на будущее - обновление токена автоматом
            #main_handler = Main()
            #return await main_handler.refresh(request)
            msg = 'Session expired! Please, login'
            return web.HTTPUnauthorized(reason=msg, body=msg)


    except jwt.DecodeError:
        msg = 'Security problem. Please, relogin!'
        return web.HTTPUnauthorized(reason=msg, body=msg)

    except jwt.ExpiredSignatureError:
        msg = 'Security problem. Your session has expired. Please login!'
        return web.HTTPUnauthorized(reason=msg, body=msg)
    except Exception as e:
        return web.HTTPBadRequest(reason=str(e), body=str(e))
    return await handler(request)


@web.middleware
async def error_middleware(request, handler):
    metrics = request.app.get('metrics')
    try:
        response = await handler(request)
        if response.status == 401:
            #await metrics.inc('logins.failed')
            return response

        if response.status != 404:
            return response
        message = response.message
        #await metrics.inc('not_found')
        return web.json_response({'success': False, 'error': message})
    except web.HTTPException as ex:

        if ex.status != 404:
            if ex.status == 401:
                #await metrics.inc('logins.failed')
                pass

            raise
        message = ex.reason
        #await metrics.inc('not_found')
        return web.json_response({'success':False,'error': message})
    except Exception as e:
        await metrics.inc('crash_500')
        #return web.json_response({'success':False,'error': str(e)}, status=500)
        raise
