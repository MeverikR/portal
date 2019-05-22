from aiohttp import web
from helpers.config import Config
from helpers.utils import DateTimeAwareEncoder
from helpers.models.clients import Client
from helpers.models.users import User
from helpers.models.params import Param
from helpers.models.log import Statistic
from helpers.db import many, one, scalar, update, insert, delete
from helpers.dataprovider import DataProvider
from helpers.validator import validate
from handlers.users import Users

#
from pprint import pprint

config = Config.get_config()


class Clients:
    """
    Класс для отображения списка клиентов
    """

    @staticmethod
    def __encode_helper(obj):
        import json
        return json.dumps(obj, cls=DateTimeAwareEncoder)

    @staticmethod
    async def get_client(id, db):
        """
        Маленький хелпер для получения одного клиента
        :param id:
        :return:
        """
        if id and str(id).isdigit() and int(id) > 0:
            # Для ссылочных полей
            client = await one(db, Client.get_by_id(int(id)))
            # выбираем основного пользователя
            main_user = await one(db, User.get_by_id(client.get('admin')))
            client['main_user'] = main_user
            # посчитаем количество пользователей клиента и покажем юзеров
            users_count = await scalar(db, User.get_count(where_=[User.client_id == str(id)]))
            client['users'] = {'count': users_count}
            return client
        else:
            return {}

    @staticmethod
    async def get_clients(ids, db):
        """
        Хелпер для много клиентов
        :param id:
        :return:
        """
        if isinstance(ids, (list,)):
            # Для ссылочных полей
            clients = await many(db, Client.get_by_id_in(ids))
            clients = clients.get('data')
            # выбираем основного пользователя
            for client in clients:
                main_user = await one(db, User.get_by_id(client.get('admin')))
                client['main_user'] = main_user
                # посчитаем количество пользователей клиента и покажем юзеров
                users_count = await scalar(db, User.get_count(where_=[User.client_id == str(client.get('id'))]))
                client['users'] = {'count': users_count}
            return clients
        else:
            return {}

    @validate(request_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 3, "maxLength": 255},
            "token": {"type": "string", "minLength": 10, "maxLength": 255},
            "adm_login": {"type": "string", "minLength": 1, "maxLength": 255},
            "adm_pass": {"type": "string", "minLength": 1, "maxLength": 255},
            "adm_email": {"type": "string", "minLength": 1, "maxLength": 255},
            "infopin": {"type": ["integer", "string"], "pattern": "^\d+$" },
            "app_id": {"type": ["integer", "string"], "pattern": "^\d+$" }
        },
        "required": ["name", "token", "adm_login", "adm_pass"],
        "additionalProperties": False
    })
    async def create(self, request):
        """
        Создать клиента нового
        :param request:
        :return:
        """

        if request.auth.get('group') != 0:
            return web.HTTPUnauthorized()  # только суперадмин может добавить клиента

        db = request.app['db']

        try:
            json = await request.json()
        except Exception as e:
            raise web.HTTPNotAcceptable(reason='Can`t create client. Data error: ' + str(e),
                                        body='Can`t create client. Data error: ' + str(e))

        if 'name' not in json \
                or 'token' not in json \
                or 'adm_login' not in json \
                or 'adm_pass' not in json:
            raise web.HTTPNotAcceptable(reason='Can`t create client. Data error. ',
                                        body='Can`t create client. Data error. ')

        # сразу проверяем токен, а то потом уже шляпа
        try:
            dt = DataProvider(json.get('token'))
            tags = await dt.get_tags()
        except Exception as e:

            raise web.HTTPNotAcceptable(reason='Can`t create client: ' + str(e),
                                        body='Can`t create client:' + str(e))

        # 0. создаем клиента
        client_ = {
            'name': json.get('name'),
            'infopin':  json.get('infopin', 0),
            'app_id': json.get('app_id', 0),
            'token': json.get('token'),
            'admin': 0
        }

        # проверяем логин

        login_exists = await scalar(db, """
            -- проверка существования логина главного админа при добавлении клиента
            SELECT id FROM users WHERE login = '%s'
            """ % json.get('adm_login'))

        if login_exists is not None:
            raise web.HTTPNotAcceptable(reason='Can`t create. User already exists with login: ' + json.get('adm_login'),
                                        body='Can`t create. User already exists with login: ' + json.get('adm_login'))
        # проверяем токен
        a_token =  json.get('token')

        token_exists = await scalar(db, """
        -- проверка токена при добавлении клиента на существование
        SELECT id FROM clients WHERE token = '%s'
        """ % a_token)

        if token_exists is not None:
            raise web.HTTPNotAcceptable(
                reason='Can`t create. Client with that token already exists: ' + json.get('token'),
                body='Can`t create. Client with that token already exists: ' + json.get('token'))




        try:
            new_client = await insert(db, Client.add(client_))
        except Exception as e:
            raise web.HTTPNotAcceptable(
                reason='Can`t create. DB Error: ' + str(e),
                body='Can`t create. DB Error: ' + str(e))

        new_client = new_client[0].get('id')
        if not new_client:
            raise web.HTTPNotAcceptable(reason='Can`t create client. Data error. ',
                                        body='Can`t create client. Data error. ')

        # 1 . создаем корневого пользователя
        usr_name = 'Администратор клиента ' + client_.get('name')
        usr_login = json.get('adm_login')
        usr_pass = json.get('adm_pass')
        usr_email = json.get('adm_email')
        usr_comment = 'Автоматически созданный администратор клиента ' + client_.get('name')


        _adm_user = {
            'name': usr_name,
            'login': usr_login,
            'password': usr_pass,
            'email_address': usr_email,
            'group_id': 1,  # администратор клиента созданный автоматом
            'client_id': new_client,
            'comment': usr_comment,

        }
        try:
            new_adm_user = await insert(db, User.add(_adm_user))
        except Exception as e:
            # стираем клиента, он типа не добавлен
            await delete(db, Client.remove([Client.id == new_client]))
            raise web.HTTPNotAcceptable(reason='Can`t create. User add DB error: ' + str(e),
                                        body='Can`t create. User add DB error: ' + str(e))

        new_adm_user = new_adm_user[0].get('id')
        if not new_adm_user:
            await delete(db, Client.remove([Client.id == new_client]))
            raise web.HTTPNotAcceptable(reason='Can`t create client. Data error. ',
                                        body='Can`t create client. Data error. ')
        # финальный штрих, привязываем админа к клиенту

        try:
            ret = await update(db, Client.update({'admin': new_adm_user}, where_=[Client.id == new_client]))
        except Exception as e:
            raise web.HTTPNotAcceptable(reason='Can`t create. Adm user to client append error: ' + str(e),
                                        body='Can`t create. Adm user to client append error: ' + str(e))


        if not tags:
            await delete(db, Client.remove([Client.id == new_client]))
            raise web.HTTPNotAcceptable(reason='Can`t create client. Token problem',
                                        body='Can`t create client. Token problem')

        tags_ids = []
        for tag in tags:
            tags_ids.append(tag.get('id'))

        usr_params = {
            'fields': config.get('app').get('fields_avaliable'),
            'filters': [],
            'tags': tags_ids,
            'allow_tags_add': True,
            'allow_tags_delete': True,
            'user_id': new_adm_user
        }
        try:
            new_params = await insert(db, Param.add(usr_params))
        except Exception as eee:
            await delete(db, Client.remove([Client.id == new_client]))
            raise web.HTTPNotAcceptable(reason='Can`t create client. Admin params creation error: ' + str(eee),
                                        body='Can`t create client. Admin params creation error: ' + str(eee))

        if not new_params:
            await delete(db, Client.remove([Client.id == new_client]))
            raise web.HTTPNotAcceptable(reason='Can`t create client. Default params creation failed!',
                                        body='Can`t create client. Default params creation failed!')

        if ret:  # если все ок
            # запишем событие
            stat = {
                'user_id': new_adm_user,
                'code': '2',
                'msg': 'New user created for client ' + str(new_client)
            }
            await insert(db, Statistic.add(stat))

            request['id'] = new_client
            return await self.get_one(request)

        else:
            await delete(db, Client.remove([Client.id == new_client]))
            raise web.HTTPNotAcceptable(reason='Can`t create client. Data error. ',
                                        body='Can`t create client. Data error. ')

    async def delete(self, request):
        """
        Удалить клиента и все что с ним связано
        :param request:
        :return:
        """
        if request.auth.get('group') != 0:
            return web.HTTPUnauthorized()  # только суперадмин может добавить клиента

        db = request.app['db']
        id = request.match_info.get('id', 0)
        # подгрузим клиента
        client = await one(db, Client.get_by_id(id))
        client_users = await many(db, User.get_by([User.client_id == id]))
        client_users_ids = [str(x.get('id')) for x in client_users.get('data')]

        if client and 'id' in client and 'admin' in client:

            del_user_result = bool(await delete(db, """
                -- грохаем пользователей %s у клиента %s
                delete from users where id in (%s)
            """ % (", ".join(client_users_ids), str(id), ", ".join(client_users_ids))))

            if not del_user_result:
                raise web.HTTPNotAcceptable(reason='Can`t delete client. Admin delete error. ',
                                            body='Can`t delete client. Admin delete error. ')

            # разлогиневаем всех удаленных пользаков
            cache = request.app.get('cache')
            for uid in client_users_ids:
                await cache.kill_cache('uid_token_' + uid)

            del_params_result = bool(await delete(db, """
                -- грохаем параметры пользователей %s у клиента %s
                delete from params where user_id in (%s)
            """ % (", ".join(client_users_ids), str(id), ", ".join(client_users_ids))))

            if not del_params_result:
                raise web.HTTPNotAcceptable(reason='Can`t delete client. Params delete error. ',
                                            body='Can`t delete client. Params delete error. ')
            del_client_result = bool(await delete(db, Client.remove([Client.id == id])))
            if not del_client_result:
                raise web.HTTPNotAcceptable(reason='Can`t delete client. DB error. ',
                                            body='Can`t delete client. DB error. ')
            # запишем событие
            stat = {
                'user_id': request.auth.get('id'),
                'code': '7',
                'msg': 'Client ' + str(id) + ' and users [' + ", ".join(client_users_ids) + '] deleted'
            }
            await insert(db, Statistic.add(stat))

            return web.json_response(
                client,
                dumps=Clients.__encode_helper,
                headers={'X-Total-Count': '1'}
            )
        else:
            raise web.HTTPNotAcceptable(reason='Can`t delete client. Params error. ',
                                        body='Can`t delete client. Params error. ')

    async def get_list(self, request):
        """
        Получить список клиентов
        :param request:
        :return: - всегда список
        """
        if request.auth.get('group') != 0:
            return web.HTTPUnauthorized()  # только суперадмин может добавить клиента

        db = request.app['db']

        # пробуем получить сразу несколько аргументов,
        # ибо чувак может прислать /?id=1&id=2&id=3

        parameters = request.rel_url.query

        search = request.query.get('q', None)
        if 'id' in parameters:
            ids = parameters.getall('id')
            # Для ссылочных полей
            clients = await Clients.get_clients(ids, db)
            # выбираем основного пользователя
            return web.json_response(
                clients,
                dumps=Clients.__encode_helper,
                headers={'X-Total-Count': str(0) if len(clients) == 0 else str(len(clients))}
            )

        # собираем все штуки для сортировки и пагинации
        limit = request.query.get('_end', '15')
        offset = request.query.get('_start', '0')

        if int(limit) - int(offset) > 0:
            limit = int(limit) - int(offset)
            limit = str(limit)

        sort = request.query.get('_sort', 'id')
        order = request.query.get('_order', 'DESC')

        # выбираем всех клиентов
        if search:

            clients = await many(db,
                                 Client.get(int(limit), int(offset),
                                            sort_=getattr(Client, sort), order_=order,
                                            where_=[Client.name.like("%" + search + "%")]

                                            )
                                 )
            clients_total = await scalar(db, Client.get_count(where_=[Client.name.like("%" + search + "%")]))
        else:
            clients = await many(db,
                                 Client.get(int(limit), int(offset),
                                            sort_=getattr(Client, sort), order_=order,

                                            )
                                 )

            clients_total = await scalar(db, Client.get_count(where_=[Client.id > 0]))

        ret = []
        for client in clients.get('data'):
            client['main_user'] = await one(db, User.get_by_id(client.get('admin')))
            client['users'] = {'count': await scalar(db, User.get_count(where_=[User.client_id == client.get('id')]))}
            ret.append(client)

        # запишем событие
        stat = {
            'user_id': request.auth.get('id'),
            'code': '8',
            'msg': 'Client list fetched [' + str(clients_total) + ']'
        }
        await insert(db, Statistic.add(stat))

        return web.json_response(
            ret,
            dumps=Clients.__encode_helper,
            headers={'X-Total-Count': str(clients_total)}
        )

    async def unset_tag(self, request):
        if request.auth.get('group') not in [1, 2]:
            return web.HTTPUnauthorized()  # только суперадмин может добавить клиента
        if not bool(request.auth.get('allow_tags_delete')):
            return web.HTTPUnauthorized()

        db = request.app['db']
        client_id = request.auth.get('client')
        client = await one(db, Client.get_by_id(client_id))
        user_id = request.auth.get('id')
        token = client.pop('token')
        dt = DataProvider(token)
        json = await request.json()
        comm_id = json.get('comm_id')
        tag_id = json.get('tag_id')

        if not comm_id or not tag_id:
            return web.HTTPNotAcceptable(reason="Communication ID or Tag ID not found in request")

        unset_result = await dt.unset_tag_communication(comm_id, tag_id)
        if 'error' not in unset_result.get('result'):
            stat = {
                'user_id': user_id,
                'code': '6',
                'msg': 'Unset tag [' + str(tag_id) + '] for communication_id [' + str(comm_id) + ']'
            }
            await insert(db, Statistic.add(stat))
            return web.json_response(
                unset_result.get('result').get('data'),
                headers={'X-Total-Count': '1'}
            )

        else:
            return web.HTTPNotAcceptable()

    async def set_tag(self, request):
        if request.auth.get('group') not in [1, 2]:
            return web.HTTPUnauthorized()

        db = request.app['db']
        client_id = request.auth.get('client')
        client = await one(db, Client.get_by_id(client_id))
        user_id = request.auth.get('id')
        token = client.pop('token')
        dt = DataProvider(token)
        json = await request.json()
        comm_id = json.get('communication_id')
        tag_id = json.get('tag_id')

        if not comm_id or not tag_id:
            return web.HTTPNotAcceptable()

        ret = await dt.set_tag_communication(comm_id, tag_id)

        if 'error' not in ret.get('result'):
            stat = {
                'user_id': user_id,
                'code': '5',
                'msg': 'Set tag [' + str(tag_id) + '] for communication_id [' + str(comm_id) + ']'
            }
            await insert(db, Statistic.add(stat))
            metrics = request.app.get('metrics')
            await metrics.inc('data_api_added_tag_count')

            return web.json_response(
                ret.get('result').get('data'),
                headers={'X-Total-Count': '1'}
            )

        else:
            metrics = request.app.get('metrics')
            await metrics.inc('data_api_failed_request_count')
            return web.HTTPNotAcceptable()

    async def create_tag(self, request):
        if request.auth.get('group') not in [1, 2]:
            return web.HTTPUnauthorized()  # только суперадмин может добавить клиента
        if request.auth.get('allow_tags_add') != 1:
            return web.HTTPUnauthorized()  # только суперадмин может добавить клиента
        db = request.app['db']
        client_id = request.auth.get('client')
        client = await one(db, Client.get_by_id(client_id))
        token = client.pop('token')
        dt = DataProvider(token)
        json = await request.json()
        name = json.get('name')

        ret = await dt.add_tag(name)
        metrics = request.app.get('metrics')
        #await metrics.inc('data_api.requests')

        if 'error' in ret:
            metrics = request.app.get('metrics')
            await metrics.inc('data_api_failed_request_count')
            raise web.HTTPNotAcceptable(
                body=ret.get('error').get('message'), reason=ret.get('error').get('message'))
        tag_id = ret.get('result').get('data').get('id')

        user_params = await one(db, Param.get_by(where_=[Param.user_id == request.auth.get('id')]))
        user_tags = user_params.pop('tags')
        user_tags.append(tag_id)
        upd = {
            'tags': user_tags
        }
        await update(db, Param.update(what_=upd, where_=[Param.user_id == request.auth.get('id')]))

        # запишем событие
        stat = {
            'user_id': request.auth.get('id'),
            'code': '12',
            'msg': 'Tag created [' + str(name) + '] with id [' + str(tag_id) + ']'
        }
        await insert(request.app['db'], Statistic.add(stat))

        # обновляем профиль пользователя в браузере прям через сокет
        import json as _json
        for uid,_ws_list in request.app['websockets'].items():
            if int(request.auth.get('id')) == int(uid):
                # просим всех клиентов пользователя обновить у себя теги
                for _ws in _ws_list:
                    try:
                        await _ws.send_str(_json.dumps({'type' : 'update_user_tag', 'payload' : {'user_tags' : user_tags, 'client_tags' : await dt.get_tags() } }))
                    except Exception as e:
                        request.app['_log'].error(str(e))

        return web.json_response(
            ret.get('result').get('data'),
            headers={'X-Total-Count': '1'}
        )

    async def get_tags(self, request):
        """
        Список тегов клиента в КМ
        """
        if request.auth.get('group') not in [1, 2]:
            return web.HTTPUnauthorized()  # только суперадмин может добавить клиента
        if request.auth.get('allow_tags_add') != 1:
            return web.HTTPUnauthorized()  # только суперадмин может добавить клиента
        db = request.app['db']

        # проверяем список тегов


        client_id = request.auth.get('client')
        client = await one(db, Client.get_by_id(client_id))
        group = request.auth.get('group')
        token = client.pop('token')
        dt = DataProvider(token)
        if int(group) == 2:
            user_id = request.auth.get('id')
            user = await one(db, User.get_full_by_id(user_id, client_id))
            if int(request.auth.get('id')) > 0 and user.get('params_enable_deleted_tags_check') is True:
                u = Users()
                await u._fix_deleted_tags(request.auth.get('id'), request.app)

            dt.set_filter([{'field': 'id', 'operator': 'in', 'value': user['params_tags']}], 'and')
            #print(dt.get_filters())
            #print(user)

        limit = request.query.get('_end', '15')
        offset = request.query.get('_start', '0')
        if int(limit) - int(offset) > 0:
            limit = int(limit) - int(offset)
            limit = str(limit)

        sort = 'name'  # str(request.query.get('_sort', 'name')).lower()
        order = str(request.query.get('_order', 'DESC')).lower()
        search = request.query.get('q')
        dt.set_sort([{'field': sort, 'order': order}])

        if search:
            tags = await dt.get_tags(limit, offset, str(search))
        else:
            tags = await dt.get_tags(limit, offset)

        if not tags:
            metrics = request.app.get('metrics')
            await metrics.inc('data_api_failed_request_count')

        # запишем событие
        stat = {
            'user_id': request.auth.get('id'),
            'code': '11',
            'msg': 'Tag list fetched [' + str(tags.get('total')) + ']'
        }
        await insert(request.app['db'], Statistic.add(stat))

        return web.json_response(
            tags.get('data'),
            headers={'X-Total-Count': tags.get('total')}
        )

    async def get_one(self, request):
        """
        Получить один конкретный клиент
        :param request:
        :return:
        """
        if request.auth.get('group') != 0:
            return web.HTTPUnauthorized()  # только суперадмин может добавить клиента

        id = request.match_info.get('id') or request.get('id') or 0
        client = await Clients.get_client(id, request.app['db'])

        # запишем событие
        stat = {
            'user_id': request.auth.get('id'),
            'code': '10',
            'msg': 'Client ONE fetched [' + str(id) + ']'
        }
        await insert(request.app['db'], Statistic.add(stat))

        return web.json_response(
            client,
            dumps=Clients.__encode_helper,
            headers={'X-Total-Count': str(0) if len(client) == 0 else str(1)}
        )

    @validate(request_schema={
        "type": "object",
        "properties": {
            "id": {"type": "integer", "minLength": 1, "minimum" : 1},
            "admin": {"type": "integer", "minLength": 1},
            "token": {"type": "string", "minLength": 10, "maxLength": 255},
            "name": {"type": "string", "minLength": 2, "maxLength": 255},
            "main_user": {"type": "object", "properties": {
                "id": {"type": "integer", "minLength": 1, "minimum" : 1},
                "login": {"type": "string", "minLength": 1,  "maxLength": 255},
                "name": {"type": "string", "minLength": 2,  "maxLength": 255},
                "password": {"type": "string", "minLength": 1, "maxLength": 255},
                "group_id": {"type": "integer", "minLength": 1, "minimum" : 1},
                "client_id": {"type": "integer", "minLength": 1, "minimum" : 1},
            }, "required" : ["id", "name", "login", "password", "group_id", "client_id"]},
            "infopin": {"type": ["integer", "string"], "pattern": "^\d+$"},
            "app_id": {"type": ["integer", "string"], "pattern": "^\d+$"}
        },
        "required": ["token", "name"],
        "additionalProperties": True
    }
    )
    async def update(self, request):
        """
        Обновление данных клиента
        :param request:
        :return:
        """
        if request.auth.get('group') != 0:
            return web.HTTPUnauthorized()  # только суперадмин может добавить клиента

        try:
            json = await request.json()
        except Exception as e:
            raise web.HTTPNotAcceptable(reason='Can`t update client. Data error: ' + str(e),
                                        body='Can`t update client. Data error: ' + str(e))

        id = request.match_info.get('id', 0)

        if 'adm_login' in json:
            adm_login = json.pop('adm_login')
            json['main_user']['adm_login'] = adm_login

        if 'adm_pass' in json:
            adm_pass = json.pop('adm_pass')
            json['main_user']['adm_pass'] = adm_pass

        if 'users' in json:
            del json['users']

        if 'id' in json:
            del json['id']

        if 'main_user' in json:
            main_user = json.pop('main_user')

            main_user_id = await scalar(request.app['db'], """
            -- получить корневого пользователя клиента
            SELECT admin FROM clients WHERE id = %d 
            """ % int(id))
            main_user_update = {
                'name': main_user.get('name'),
                'login': main_user.get('login'),
                'password': main_user.get('password'),
            }

            a_login = main_user.get('login')

            login_exists = await scalar(request.app['db'], """
            -- проверка существования логина при обновлении клиента
            SELECT id FROM users WHERE login = '%s' AND id != %d
            """ % (a_login, int(main_user_id)))

            if login_exists is not None:
                # значит есть
                request.app['_log'].error('Error while client update user login already exists: ' + str(login_exists))
                raise web.HTTPNotAcceptable(reason='Can`t update client. User login already exists.',
                                            body='Can`t update. User login already exists.')


            try:
                main_user_res = await update(request.app['db'],
                                         User.update(what_=main_user_update, where_=[User.id == main_user_id]))

                if main_user_res is not None:
                    request.app['_log'].info('Сlient main admin update success: ' + str(main_user_id) + ' client ' + str(id))

            except Exception as ee:
                request.app['_log'].error('Error while client update in adm_user: ' + str(ee))
                raise web.HTTPNotAcceptable(reason='Can`t update. Server error: ' + str(ee),
                                            body='Can`t update. Server error: ' + str(ee))

        tk = json.get('token')

        token_exists = await scalar(request.app['db'], """
            -- проверка токена на существование
            SELECT id FROM clients WHERE token = '%s' AND id != %d; 
        """ % (tk, int(id) ))

        if token_exists is not None:
            # значит уже есть
            request.app['_log'].error('Error while client update token already exists: ' + str(tk))
            raise web.HTTPNotAcceptable(reason='Can`t update client. Token already exists.',
                                        body='Can`t update. Token already exists')

        try:
            dt = DataProvider(tk)
            tags = await dt.get_tags()
        except Exception as e:
            raise web.HTTPNotAcceptable(reason='Can`t create client: ' + str(e),
                                        body='Can`t create client:' + str(e))

        res = await update(request.app['db'], Client.update(what_=json, where_=[Client.id == id]))

        client = await Clients.get_client(id, request.app['db'])
        client['result'] = res if res else 0

        await scalar(request.app['db'], Statistic.add({
            'user_id': request.auth.get('id'),
            'code': '6',
            'msg': 'Сlient [' + str(id) + '] updated'
        }))

        return web.json_response(
            client,
            dumps=Clients.__encode_helper,
            headers={'X-Total-Count': str(0) if len(client) == 0 else str(1)}
        )
