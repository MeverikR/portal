from aiohttp import web
from helpers.config import Config
from helpers.utils import DateTimeAwareEncoder, users_join_cleaner, fields_preparator, group_from_labels, \
    group_from_labels_many
from helpers.models.params import Param
from helpers.models.users import User
from helpers.models.clients import Client
from helpers.models.groups import Group
from helpers.models.log import Statistic
from helpers.db import many, one, update, insert, delete, scalar
from helpers.dataprovider import DataProvider
from helpers.validator import validate
from handlers.main import Main

config = Config.get_config()
LIMIT = config.get('app').get('defaults').get('limit')


class Users:
    """
    Класс для отображения списка пользователей
    """

    def __encode_helper(self, obj):
        import json
        return json.dumps(obj, cls=DateTimeAwareEncoder)

    async def _fix_deleted_tags(self, user_id, app):
        """
        Если в КМ удалили теги, то у нас они обновятся не сразу
        Этот метод чистит удаленные теги из настроек юзера
        :param user_id:
        :param app:
        :return:
        """
        try:
            db = app.get('db')

            user = (await one(db,
                              User.join(Param, 1, 0,
                                        on=User.id == Param.user_id, where_=[User.id == user_id])
                              ))
            user['group'] = await one(db, Group.get_by_id(user.get('users_group_id')))
            user = users_join_cleaner(user)
            user['client'] = await one(db, Client.get_by_id(user.get('client_id')))
            client_token = user['client'].pop('token')
            dp = DataProvider(client_token)
            all_ava_tags = await dp.get_tags() # список тегов клиента
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

            # просим клиента обновить профиль
            # обновляем профиль пользователя в браузере прям через сокет
            import json as _json
            for uid, _ws_list in app['websockets'].items():
                if int(user_id) == int(uid):
                    # просим всех клиентов пользователя обновить у себя теги
                    for _ws in _ws_list:
                        try:
                            await _ws.send_str(_json.dumps({'type': 'update_user_tag',
                                                            'payload': {'user_tags': user['params']['tags'],
                                                                        'client_tags': all_ava_tags}}))
                        except Exception as e:
                            app['_log'].error(str(e))


        except Exception as ee:
            app['_log'].error('Tags sync error: ' + str(ee))
            return False
        return True


    def _enum_rows(self, data):
        """
        После джойна с лабелями пересчитать строчки и добавить всем им ID
        :return:
        """
        data_ = data.get('data')
        keyed_data = []
        for x in data_:
            x['id'] = x.pop('users_id')
            keyed_data.append(x)

            flds = x.pop('params_fields')
            tags = x.get('params_tags')
            tags_ids = []
            for tag in tags:
                tags_ids.append(tag.get('id'))

            new_fields = []
            _fields = []
            for field in flds:
                new_fields.append({'id': field, 'name': field})
                _fields.append(field)
                x['params_fields'] = new_fields
                x['tags'] = tags_ids
                x['_fields'] = _fields
        del data_

        return keyed_data

    async def delete(self, request):
        """
        Удаление пользователя
        :param request:
        :return:
        """
        db = request.app['db']
        auth = request.auth
        if request.auth.get('group') != 1:
            return web.HTTPUnauthorized()
        if not auth.get('client'):
            return web.HTTPUnauthorized()

        id = request.match_info.get('id', 0)

        user = await one(db, User.get_by([User.id == id, User.client_id == auth.get('client')]))

        del_user_result = bool(await delete(db, User.remove([User.id == id, User.client_id == auth.get('client')])))
        del_params_result = bool(await delete(db, Param.remove([Param.user_id == user.get('id')])))

        if not del_user_result:
            raise web.HTTPNotAcceptable(reason='Can`t delete user. Try again later ',
                                        body='Can`t delete user. Try again later')

        # статистика
        stat = {
            'user_id':auth.get('id'),
            'code': '17',
            'msg': 'User deleted [' + str(id) + ']'
        }
        await insert(db, Statistic.add(stat))

        # разлогиневаем удаленного
        cache = request.app.get('cache')
        await cache.kill_cache('uid_token_' + str(id))

        return web.json_response(
            user,
            dumps=self.__encode_helper,
            headers={'X-Total-Count': '1'}
        )


    @validate(request_schema={
        "type" : "object",
        "properties" : {
            "name": {"type": "string", "minLength": 1, "maxLength": 255},
            "login": {"type": "string", "minLength": 1, "maxLength": 255},
            "password": {"type": "string", "minLength": 1, "maxLength": 255},
            "group_id": {"type": ["string", "number"],   "pattern": "^([1-2]{1})$"},
        },
        "required": ["name", "login", "password", "group_id"],
        "additionalProperties": True
    })
    async def create(self, request):
        """
        Создание пользователя
        :param request:
        :return:
        """
        db = request.app['db']
        auth = request.auth
        # пользаков можт добавлять только админ
        if request.auth.get('group') != 1:
            return web.HTTPUnauthorized()

        try:
            data = await request.json()
        except Exception as e:
            return web.json_response({'success': False, 'error': str(e)}, status=500)

        user_neo = {
            'name': data.get('name'),
            'login': data.get('login'),
            'email_address': data.get('email_address'),
            'password': data.get('password'),
            'comment': data.get('comment'),
            'client_id': auth.get('client'),
            'group_id': data.get('group_id')
        }
        try:
            new_user = await insert(db, User.add(user_neo))
        except Exception as e:
            raise web.HTTPNotAcceptable(reason='Can`t create. User already exists with login: ' + data.get('login'),
                                        body='Can`t create. User already exists with login: ' + data.get('login'))

        new_user = new_user[0].get('id')
        if not new_user:
            raise web.HTTPNotAcceptable(reason='Can`t create user. Data error. ',
                                        body='Can`t create user. Data error. ')

        usr_params = {
            'fields': data.get('params').get('fields') if data.get('params') else [],
            'filters': data.get('params').get('filters') if data.get('params') else [],
            'tags': data.get('params').get('tags') if data.get('params') else [],
            'allow_tags_add': bool(data.get('params').get('allow_tags_add')) if data.get('params') else False,
            'allow_tags_delete': bool(data.get('params').get('allow_tags_delete')) if data.get('params') else False,
            'hide_sys_id': bool(data.get('params').get('hide_sys_id')) if data.get('params') else False,
            'hide_sys_aon': bool(data.get('params').get('hide_sys_aon')) if data.get('params') else False,
            'hide_sys_player': bool(data.get('params').get('hide_sys_player')) if data.get('params') else False,
            'hide_sys_static': bool(data.get('params').get('hide_sys_static')) if data.get('params') else False,
            'enable_deleted_tags_check': bool(data.get('params').get('enable_deleted_tags_check')) if data.get('params') else False,
            'user_id': new_user
        }

        if usr_params.get('filters') is None or usr_params.get('filters') == 'null' or usr_params.get('filters') == '':
            usr_params['filters'] = []
        if usr_params.get('fields') is None or usr_params.get('fields') == 'null' or usr_params.get('fields') == '':
            usr_params['fields'] = []
        if usr_params.get('tags') is None or usr_params.get('tags') == 'null' or usr_params.get('tags') == '':
            usr_params['tags'] = []

        new_params = await insert(db, Param.add(usr_params))

        if not new_params:
            raise web.HTTPNotAcceptable(reason='Can`t create user. Default params creation failed!',
                                        body='Can`t create user. Default params creation failed!')

        # статистика
        stat = {
            'user_id': request.auth.get('id'),
            'code': '3',
            'msg': 'User created [' + str(new_user) + '] params [' + str(new_params) + ']'
        }
        await insert(db, Statistic.add(stat))

        request['id'] = new_user

        return await self.get_one(request)



    @validate(request_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 255},
            "login": {"type": "string", "minLength": 1, "maxLength": 255},
            "password": {"type": "string", "minLength": 1, "maxLength": 255},
            "group_id": {"type": ["string", "number"],   "pattern": "^([1-2]{1})$"},
            "email_address" : {"type": ["string", "null"], "format" : "idn-email"},
            "comment" : {"type": ["string", "null"], "maxLength": 255},
        },
        "required": ["name", "login", "password", "group_id"],
        "additionalProperties": True
    })
    async def update(self, request):
        """
        Обновить данные по пользователю
        :param requset:
        :return:
        """
        if request.auth.get('group') != 1:
            return web.HTTPUnauthorized()  # только админ может добавлять и менять

        try:
            id = int(request.match_info.get('id', 0))
        except Exception as e:
            return web.HTTPNotAcceptable(reason='Can`t update user. Data error: ' + str(e),
                                  body='Can`t update user. Data error: ' + str(e))


        print('Update request started for user: ' + str(id))

        try:
            data = await request.json()
        except Exception as e:

            return web.HTTPNotAcceptable(reason='Can`t update user. Data error: ' + str(e),
                                  body='Can`t update user. Data error: ' + str(e))

#        if int(id) != int(data.get('id')):
#            return web.HTTPNotAcceptable(reason='Can`t update user. Data error: id in request not match id in body',
#                                  body='Can`t update user. Data error: id in request not match id in body ')
        db = request.app['db']
        not_n_fields = ['client_id', 'id', 'group', 'client']
        for el in not_n_fields:
            if el in data:
                data.pop(el)

        if 'params' in data:
            params = data.pop('params')
            if params.get('filters') is None or params.get('filters') == 'null' or params.get('filters') == '':
                params['filters'] = []
            else:
                for num, filter in enumerate(params.get('filters')):
                    if 'filters' not in filter:
                        del params['filters'][num]
                    if len(filter.get('filters')) <= 0:
                        del params['filters'][num]

            if params.get('fields') is None or params.get('fields') == 'null' or params.get('fields') == '':
                params['fields'] = []
            if params.get('tags') is None or params.get('tags') == 'null' or params.get('tags') == '':
                params['tags'] = []

            if 'user_id' in params:
                params.pop('user_id')

            if 'id' in params:
                params.pop('id')



            params_id = await scalar(db,
            """
            -- получить ID настроек для пользователя
            SELECT id FROM params WHERE user_id = %d            
            """ % id
                                     )

            res_params = await update(db, Param.update(what_=params, where_=[Param.id == params_id]))
            stat = {
                'user_id': request.auth.get('id'),
                'code': '94',
                'msg': 'Params for user ['+str(id)+'] updated ' + str(res_params)
            }
            await insert(db, Statistic.add(stat))


        try:
            res_user = await update(db, User.update(what_=data, where_=[User.id == id]))
        except Exception as ee:
            request.app['_log'].error('Error while user update: ' + str(ee))
            raise web.HTTPNotAcceptable(reason='Can`t update. User already exists with login',
                                        body='Can`t update. User already exists with login')


        if int(res_user) > 0:
            request['id'] = id
            # статистика
            stat = {
                'user_id': request.auth.get('id'),
                'code': '4',
                'msg': 'User updated ' + str(id)
            }
            await insert(db, Statistic.add(stat))

            ## DEPRECATED! Больше не выходим юзера. Просто обновляем ему профиль через сокет
            ## надо заставить юзера перевойти, ибо мы поменяли ему профиль.
            ## разлогиневаем юзера, пусть перезайдет.
            #cache = request.app.get('cache')
            #await cache.kill_cache('uid_token_' + str(id))
            import json as _json
            m = Main()
            profile = await m.get_profile(id, app=request.app)

            for uid, _ws_list in request.app['websockets'].items():
                if int(id) == int(uid):
                    # просим всех клиентов пользователя обновить у себя настройки профиля
                    # если у них там что-то не обновится, потребуется перезайти
                    for _ws in _ws_list:
                        try:
                            if profile:
                                await _ws.send_str(_json.dumps({'type': 'update_profile',
                                                            'payload': profile}, cls=DateTimeAwareEncoder))
                        except Exception as e:
                            request.app['_log'].error(str(e))


            return await self.get_one(request)

        else:
            return web.json_response({'success': False, 'error': 'Обновление не удалось!'}, status=500)

    async def get_list(self, request):
        """
        Получить список пользователй
        :param request:
        :return: - всегда список
        """
        db = request.app['db']
        auth = request.auth
        if auth.get('group') != 1:
            return web.HTTPUnauthorized()  # только админ может видеть пользователей своих

        # замечено, что иногда при некоторых связях реактадмину надо еще один роут

        parameters = request.rel_url.query
        search = request.query.get('q', None)
        group_id = request.query.get('group_id', None)

        if 'id' in parameters:
            ids = parameters.getall('id')
            users = await many(db,
                               User.get_full_in_ids(ids, auth.get('client'), where_=[User.id != auth.get('id')])
                               )
            resp = group_from_labels_many(users)
            return web.json_response(
                resp.get('data'),
                dumps=self.__encode_helper,
                headers={'X-Total-Count': resp.get('total')}
            )

        # собираем все штуки для сортировки и пагинации
        limit = request.query.get('_end', LIMIT)
        offset = request.query.get('_start', '0')

        if int(limit) - int(offset) > 0:
            limit = int(limit) - int(offset)
            limit = str(limit)

        sort = request.query.get('_sort', 'id')
        order = request.query.get('_order', 'DESC')
        if search:
            query = User.get_full(request.auth.get('client'), limit, offset, sort, order,
                                  where_=[
                                      User.id != auth.get('id'),
                                      User.name.like("%" + search + "%")
                                  ])

            users_total = await scalar(db, User.get_count(
                where_=[
                    User.id != auth.get('id'),
                    User.name.like("%" + search + "%"),
                    User.client_id == request.auth.get('client')
                ]))


        elif group_id:
            query = User.get_full(request.auth.get('client'), limit, offset, sort, order,
                                  where_=[
                                      User.id != auth.get('id'),
                                      User.group_id == group_id,
                                  ])

            users_total = await scalar(db, User.get_count(
                where_=[User.id != auth.get('id'),
                        User.group_id == group_id,
                        User.client_id == request.auth.get('client')
                        ]))
        else:
            users_total = await scalar(db, User.get_count(
                where_=[
                    User.id != auth.get('id'),
                    User.client_id == request.auth.get('client')
                ]))

            query = User.get_full(request.auth.get('client'), limit, offset, sort, order,
                                  where_=[User.id != auth.get('id')])

        users = await many(db, query)

        resp = group_from_labels_many(users)

        # статистика
        stat = {
            'user_id': str(auth.get('id')),
            'code': '14',
            'msg': 'Users list fetched [' + str(users_total) + ']'
        }
        await insert(db, Statistic.add(stat))

        return web.json_response(
            resp.get('data'),
            dumps=self.__encode_helper,
            headers={'X-Total-Count': str(users_total)}
        )

    async def get_one(self, request):
        """
        Получить один конкретный пользователь
        :param request:
        :return:
        """
        if request.auth.get('group') != 1:
            return web.HTTPUnauthorized()  # только админ может видеть пользователей своих

        db = request.app['db']
        # обновить список тегов клиента администратора

        client = await one(db, Client.get_by_id(request.auth.get('client')))
        client_token = client.get('token')
        dp = DataProvider(client_token)
        all_ava_tags = await dp.get_tags()  # список тегов клиента


        import json as _json
        for uid, _ws_list in request.app['websockets'].items():
            if int(request.auth.get('id')) == int(uid):
                # просим всех клиентов пользователя обновить у себя настройки профиля
                # если у них там что-то не обновится, потребуется перезайти
                for _ws in _ws_list:
                    try:
                        if all_ava_tags:
                            await _ws.send_str(_json.dumps({'type': 'update_client_tags',
                                                            'payload': all_ava_tags}, cls=DateTimeAwareEncoder))
                    except Exception as e:
                        request.app['_log'].error(str(e))

        user_id = request.match_info.get('id') or request.get('id') or 0

        if int(user_id)> 0:
            await self._fix_deleted_tags(user_id, request.app)



        user = await one(db, User.get_full_by_id(user_id, request.auth.get('client')))

        user = group_from_labels(user)

        # статистика
        stat = {
            'user_id': str(request.auth.get('id')),
            'code': '15',
            'msg': 'Users fetched [' + str(user_id) + ']'
        }
        await insert(db, Statistic.add(stat))

        return web.json_response(
            user,
            dumps=self.__encode_helper,
            headers={'X-Total-Count': str(0) if len(user) == 0 else str(1)}
        )
