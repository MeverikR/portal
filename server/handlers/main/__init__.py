import logging, base64
from aiohttp import web, WSMsgType
from helpers.config import Config
from helpers.utils import DateTimeAwareEncoder, users_join_cleaner, fields_preparator
from helpers.models.params import Param
from helpers.models.users import User
from helpers.models.clients import Client
from helpers.models.groups import Group
from helpers.models.log import Statistic
from helpers.db import one, scalar, update
from helpers.dataprovider import DataProvider

import json, jwt
from datetime import datetime, timedelta

config = Config.get_config()
logger = logging.getLogger()

SUPERADMIN_LOGIN = config.get('app').get('superuser').get('login')
SUPERADMIN_PASS = config.get('app').get('superuser').get('password')

JWT_EXP_DELTA_SECONDS = int(config.get('app').get('security').get('jwt_expire_seconds'))
JWT_SECRET = str(config.get('app').get('security').get('jwt_secret'))
JWT_ALGORITHM = str(config.get('app').get('security').get('jwt_algorithm'))


class Main:
    """
    Класс для базового URL /
    """

    @staticmethod
    async def __check_credentials(db_engine, username, password):
        if username == SUPERADMIN_LOGIN and password == SUPERADMIN_PASS:
            return True  # суперадмин ОКай!

        try:
            # у нас пока не будет хешей, ибо народ забывает пароли
            user = (await one(db_engine, User.get(
                1, 0, where_=[User.login == username, User.password == password]
            )))
            print(user)
        except Exception as e:
            print(e)
            return False

        if user:
            return True

        return False

    def __encode_helper(self, obj):

        return json.dumps(obj, cls=DateTimeAwareEncoder)

    async def index_post(self, request):
        return web.json_response({
            'success': True
        })


    async def index(self, request):
        return web.json_response({
            'success': True
        })

    async def refresh(self, request):
        """
        Для обновления профиля пользователя
        Достается исключительно из мидлвари,
         в роуты добавлять не надо его
        :param request:
        :return:
        """
        app = request.app
        auth = request.auth
        user_id = auth.get('id')
        db = app.get('db')

        user = (await one(db,
                          User.join(Param, 1, 0,
                                    on=User.id == Param.user_id, where_=[User.id == user_id])
                          ))
        # подтянем группы, потом сделаю одним запросом
        user['group'] = await one(db, Group.get_by_id(user.get('users_group_id')))
        user = users_join_cleaner(user)
        user['client'] = await one(db, Client.get_by_id(user.get('client_id')))
        client_token = user['client'].pop('token')
        dp = DataProvider(client_token)
        all_ava_tags = await dp.get_tags()
        # фикс удаленных тегов у клиента
        _tg_ids = [int(x.get('id')) for x in all_ava_tags.copy()]
        _rem_tags = []
        for u_tag in user.get('params').get('tags'):
            if int(u_tag) not in _tg_ids:
                _rem_tags.append(int(u_tag))
                # удаляем тег
        if len(_rem_tags) > 0:
            user['params']['tags'] = [x for x in user.get('params').get('tags') if x not in _rem_tags]
            await update(db, Param.update(what_={'tags': user['params']['tags']},
                                          where_=[Param.id == user['params']['id']]))

        user['client']['tags_available'] = all_ava_tags
        user['client']['fields_available'] = fields_preparator(config.get('app').get('fields_avaliable'))
        del user['password']
        payload = {
            'name': user['name'],
            'id': user['id'],
            'client': user['client_id'],
            'group': user['group_id'],
            'allow_tags_add': int(user['params']['allow_tags_add']),
            'allow_tags_delete': int(user['params']['allow_tags_delete']),
        }

        payload['exp'] = datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
        payload['iat'] = datetime.utcnow() - timedelta(seconds=1)
        payload['nbf'] = datetime.utcnow() - timedelta(seconds=1)

        jwt_token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM, json_encoder=DateTimeAwareEncoder)
        token = jwt_token.decode('utf-8')
        # регистрируем токен юзера и вход
        await scalar(db, Statistic.add({
            'user_id': user.get('id'),
            'code': '100',
            'msg': token
        }))

        cache = app.get('cache')
        metrics = app.get('metrics')
        await metrics.inc('jwt_issued_count')

        _already_in_redis_tokens = await cache.get_cache('uid_token_' + str(user['id']))
        if not _already_in_redis_tokens:
            _already_in_redis_tokens = []

        _already_in_redis_tokens.append(token)
        await cache.set_cache('uid_token_' + str(user['id']), _already_in_redis_tokens)
        await cache.expire_cache('uid_token_' + str(user['id']), (JWT_EXP_DELTA_SECONDS - 2))

        return web.json_response({'token': token, 'user': user}, dumps=self.__encode_helper, status=426) # 426 - Upgrade Required

    async def logout(self, request):
        """
        Удаляем токен из редиса
        :param request:
        :return:
        """
        app = request.app
        cache = app.get('cache')
        auth = request.auth
        user_id = auth.get('id')
        token = str(request.headers.get('authorization')).replace('Bearer ', '')

        logger.debug('Logout for token: ' + token)

        if user_id:
            token_from_redis = await cache.get_cache('uid_token_' + str(user_id)) or []
            token_from_redis.remove(token)
            if len(token_from_redis) != 0:
                await cache.set_cache('uid_token_' + str(user_id), token_from_redis)
                await cache.expire_cache('uid_token_' + str(user_id), (JWT_EXP_DELTA_SECONDS - 2))

            else:
                await cache.kill_cache('uid_token_' + str(user_id))

            return web.json_response({'success' : True})
        else:
            return web.json_response({'success': False}, status=401)

    async def get_profile(self, id, app):
        """
        Выгрузить профиль пользователя
        :param id:
        :param app:
        :return:
        """
        db = app.get('db')
        user = (await one(db,
                          User.join(Param, 1, 0,
                                    on=User.id == Param.user_id, where_=[User.id == id])
                          ))
        user['group'] = await one(db, Group.get_by_id(user.get('users_group_id')))
        user = users_join_cleaner(user)
        user['client'] = await one(db, Client.get_by_id(user.get('client_id')))
        client_token = user['client'].pop('token')
        dp = DataProvider(client_token)
        all_ava_tags = await dp.get_tags()
        # фикс удаленных тегов у клиента
        _tg_ids = [int(x.get('id')) for x in all_ava_tags.copy()]
        _rem_tags = []
        for u_tag in user.get('params').get('tags'):
            if int(u_tag) not in _tg_ids:
                _rem_tags.append(int(u_tag))
                # удаляем тег
        if len(_rem_tags) > 0:
            user['params']['tags'] = [x for x in user.get('params').get('tags') if x not in _rem_tags]
            await update(db, Param.update(what_={'tags': user['params']['tags']},
                                          where_=[Param.id == user['params']['id']]))

        user['client']['tags_available'] = all_ava_tags
        user['client']['fields_available'] = fields_preparator(config.get('app').get('fields_avaliable'))
        del user['password']

        return user




    async def login(self, request):
        """
        Основной роут авторизации
        """
        app = request.app
        try:
            #form = await request.json()
            form = str(await request.read(), encoding='utf-8')
            logger.debug("Login base64encoded: " + str(form))
            form = json.loads(str( base64.b64decode(form), encoding='utf-8'))
            logger.debug("Login decoded json: " + str(json.dumps(form)))
            login = form.get('username')
            password = form.get('password')
        except Exception as e:
            # если не распарсится джсон - все ок
            login = ''
            password = ''

        db = app.get('db')

        if await self.__check_credentials(db, login, password):
            # доработаем суперадмина
            if login == SUPERADMIN_LOGIN and password == SUPERADMIN_PASS:
                user = User.get_superadmin()
            else:

                # ВАЖНО! Логин уникальное поле! Это надо учесть при добавлении роли
                user = (await one(db,
                                  User.join(Param, 1, 0,
                                            on=User.id == Param.user_id, where_=[User.login == login])
                                  ))
                # подтянем группы, потом сделаю одним запросом
                user['group'] = await one(db, Group.get_by_id(user.get('users_group_id')))
                user = users_join_cleaner(user)
                user['client'] = await one(db, Client.get_by_id(user.get('client_id')))
                client_token = user['client'].pop('token')
                dp = DataProvider(client_token)
                all_ava_tags = await dp.get_tags()
                # фикс удаленных тегов у клиента
                _tg_ids = [ int(x.get('id')) for x in all_ava_tags.copy() ]
                _rem_tags = []
                for u_tag in user.get('params').get('tags'):
                    if int(u_tag) not in _tg_ids:
                        _rem_tags.append(int(u_tag) )
                        # удаляем тег
                if len(_rem_tags) > 0:
                    user['params']['tags'] =  [x for x in user.get('params').get('tags') if x not in _rem_tags]
                    await update(db, Param.update(what_={'tags' : user['params']['tags']  }, where_=[Param.id == user['params']['id'] ] ))

                user['client']['tags_available'] = all_ava_tags
                user['client']['fields_available'] = fields_preparator(config.get('app').get('fields_avaliable'))
                del user['password']
            # генерим юзеру токен
            payload = {
                'name': user['name'],
                'id': user['id'],
                'client': user['client_id'],
                'group': user['group_id'],
                'allow_tags_add': int(user['params']['allow_tags_add']),
                'allow_tags_delete': int(user['params']['allow_tags_delete']),
            }

            payload['exp'] = datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
            payload['iat'] = datetime.utcnow() - timedelta(seconds=1)
            payload['nbf'] = datetime.utcnow() - timedelta(seconds=1)

            jwt_token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM, json_encoder=DateTimeAwareEncoder)
            token = jwt_token.decode('utf-8')
            # регистрируем токен юзера и вход
            await scalar(db, Statistic.add({
                'user_id': user.get('id'),
                'code': '1',
                'msg': token
            }))
            logger.debug("User ["+ str(user.get('id'))  +"] has now token: [" + str(token) + "]")
            metrics = app.get('metrics')
            await metrics.inc('jwt_issued_count')

            # добавляем токен в редис, в мидлвари будем проверять его наличие
            cache = app.get('cache')
            _already_in_redis_tokens = await cache.get_cache('uid_token_' + str(user['id']))
            if not _already_in_redis_tokens:
                _already_in_redis_tokens = []

            _already_in_redis_tokens.append(token)
            await cache.set_cache('uid_token_' + str(user['id']), _already_in_redis_tokens)
            await cache.expire_cache('uid_token_' +str(user['id']), (JWT_EXP_DELTA_SECONDS-2) )

            logger.debug(json.dumps(user, cls=DateTimeAwareEncoder))
            return web.json_response({'token': token, 'user' : user}, dumps=self.__encode_helper)

        logger.debug('Login FAILED!')
        raise web.HTTPUnauthorized(
            body=b'Invalid username/password combination')

    async def websocket_handler(self, request):
        """
        Обработка задач WebSocket
        Нужен этот роут для автоматического
        Обновления данных профиля клиента
        Как только админ(ы) что-то поменяли в профиле юзера
        Мы не будем его релогинить, а просто обновим профил у клиента
        :param request:
        :return:
        """
        logger.debug('WebSocket connection starting...')

        try:
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            logger.debug('WebSocket connection started!')

            # обработчик всех сообщений из ws
            async for msg in ws:
                # получили сообщение
                logger.debug('WS-MSG: [' + str(msg) + ']' )
                if msg.type == WSMsgType.TEXT:
                    # если сообщение текстовое
                    logger.debug('WS-MSG-TEXT-DATA: [' + str(msg.data) + ']')
                    # пробуем сделать из сообщения JSON, если будет ошибка, значит прислали шлак
                    if msg.data == 'close' or msg.data == 'disconnect' or msg.data == 'drop' or msg.data == 'exit':
                        await ws.close()
                    else:
                        try:
                            event_data = json.loads(msg.data)

                            logger.debug('WS-MSG-JSON-LOADED')
                            logger.debug(json.dumps(event_data ))

                            if event_data.get('type') == 'auth':
                                logger.debug('User auth from WS')
                                pl = event_data.get('payload')
                                logger.debug('User WS token: ' + str(pl))

                                jwt_token = pl.strip('"').strip("'")
                                auth = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                                logger.debug('User WS AUTH SUCCESS: ' + str( json.dumps(auth)))
                                print(auth)
                                if auth and auth.get('id'):
                                    if not request.app['websockets'].get(auth.get('id')):
                                        request.app['websockets'][auth.get('id')] = [ws]
                                    else:
                                        # уже есть коннекты от юзера под его логином
                                        request.app['websockets'][auth.get('id')].append(ws)


                        except Exception as e:
                            logger.error('WS-DATA-ERROR: not a json string fetched from client: ' + str(e))
                            raise


            logger.debug('WebSocket connection closed.')
            return ws

        except Exception as e:
            logger.error('ERROR in WebScoket handler: ' + str(e))



