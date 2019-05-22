from datetime import datetime
from dateutil.relativedelta import *
from aiohttp import web
from helpers.config import Config

from helpers.utils import DateTimeAwareEncoder, fields_preparator
from helpers.dataprovider import DataProvider
from helpers.models.params import Param
from helpers.models.users import User
from helpers.models.clients import Client
from helpers.models.groups import Group
from helpers.models.log import Statistic
from helpers.db import many, one, update, insert, delete, scalar

#
from pprint import pprint

config = Config.get_config()


class Statistics:
    """
    Класс для отображения статистики
    """

    async def listen(self, request):
        """
        Записать событие прослушки трека
        :param request:
        :return:
        """
        auth = request.auth
        group = auth.get('group')

        if group not in [0, 1, 2]:
            return web.HTTPUnauthorized()

        user_id = auth.get('id')

        if user_id == None or user_id == '':
            return web.HTTPUnauthorized()

        communication_id = request.query.get('id')
        if communication_id:
            communication_id = str(communication_id).replace('_id', '')

        db = request.app['db']

        is_already_listen = await scalar(db, """
        SELECT id FROM statistics WHERE code=30 AND msg='%s' 
        """ % communication_id)
        is_already_listen = True if int(is_already_listen if is_already_listen else False) > 0 else False

        if not is_already_listen:
            metrics = request.app.get('metrics')
            await metrics.inc('listened_call_count')
            await scalar(db, Statistic.add({
                'user_id': user_id,
                'code': 30,
                'msg': communication_id
            }))

        return web.json_response({
            'success': True
        })

    async def dash(self, request):
        """
        отдаем в зависимости от клиента
        инфу по статистике для дашборда
        :param request:
        :return:
        """
        auth = request.auth
        group = auth.get('group')

        if group not in [0, 1, 2]:
            return web.HTTPUnauthorized()

        user_id = auth.get('id')

        if user_id == None or user_id == '':
            return web.HTTPUnauthorized()

        db = request.app['db']

        user_id_from_request = request.match_info.get('id') or request.get('id') or 0

        if int(user_id_from_request ) != int(user_id):
            return web.HTTPUnauthorized()

        if group == 0:
            # суперадмин
            all_clients_count = await scalar(db, """
            -- получить кол-во клиентов всего
                SELECT COUNT(id) FROM clients WHERE clients.token <> '';
            """)
            all_users_count = await scalar(db, """
            -- получить кол-во юзеров
            SELECT COUNT(id) FROM users WHERE users.client_id > 0 AND users.group_id = 2;
            """)

            all_admins_count = await scalar(db, """
            -- получить кол-во админов
            SELECT COUNT(id) FROM users WHERE users.client_id > 0 AND users.group_id = 1;
            """)

            logins = await scalar(db, """
            -- получить кол-во токенов за сегодня
            select count(id) from statistics where code = 1 and (created_at between date_trunc('day', now()) and now() ); 
            """)

            tags_seted = await  scalar(db, """
            -- получить кол-во тегов проставлено за сегодня
            select count(id) from statistics where code = 5 and (created_at between date_trunc('day', now()) and now() ); 
            
            """)

            tags_unseted = await scalar(db, """
            -- получить кол-во тегов снято за сегодня
            select count(id) from statistics where code = 6 and (created_at between date_trunc('day', now()) and now() ); 

            """)

            tracks_listened = await scalar(db, """
            -- получить кол-во прослушанных треков
            select count(id) from statistics where code = 30 and (created_at between date_trunc('day', now()) and now() ); 

            """)

            return web.json_response({
                'id' : user_id,
                'group' : group,
                'all_clients_count': all_clients_count,
                'all_users_count': all_users_count,
                'all_admins_count': all_admins_count,
                'logins': logins,
                'tags_seted': tags_seted,
                'tags_unseted': tags_unseted,
                'tracks_listened': tracks_listened

            })

        if group == 1:
            # админ
            my_listeners = await many(db, """
            -- получить id юзеров клиента 
                select id from users where client_id = %s
            """ % auth.get('client'))
            my_listeners = [str(h.get('id')) for h in my_listeners.get('data')]

            all_users_count = await scalar(db, """
            -- получить кол-во юзеров
            SELECT COUNT(id) FROM users WHERE users.client_id = %s;
            """ % auth.get('client'))

            all_listeners = await scalar(db, """
            -- получить кол-во юзеров слухачей
            SELECT COUNT(id) FROM users WHERE users.client_id = %s AND users.group_id = 2;
            """ % auth.get('client'))

            tracks_listened = await scalar(db, """
            -- получить кол-во прослушанных треков
            select count(id) from statistics where code = 30 and user_id in (%s) ; 
            """ % ",".join(my_listeners))

            tracks_listened_today = await scalar(db, """
            -- получить кол-во прослушанных треков за сегодня
            select count(id) from statistics where code = 30 and user_id in (%s) 
            and (created_at between date_trunc('day', now()) and now() ) ; 
            """ % ",".join(my_listeners))

            best_user = await one(db, """
            -- получить лучший пользователь
            select user_id, count(user_id) as cnt from statistics where code = 30 and user_id in (%s)  group by user_id order by cnt DESC LIMIT 1 OFFSET 0
            """ % ",".join(my_listeners))

            if best_user:
                best_user = await scalar(db,
            """
                -- выбрать имя активного пользователя
                select name from users where id = %s
            """ % best_user.get('user_id') or 0)

            return web.json_response({
                'id': user_id,
                'group': group,
                'all_users_count': all_users_count,
                'all_listeners': all_listeners,
                'tracks_listened_all': tracks_listened,
                'tracks_listened_today': tracks_listened_today,
                'best_user': best_user or '[Недостаточно данных]'
            })

        if group == 2:
            # слухач

            tracks_listened = await scalar(db, """
             -- получить кол-во прослушанных треков
             select count(id) from statistics where code = 30 and user_id = %s; 
             """ % user_id)

            tracks_listened_last = await scalar(db, """
             -- получить кол-во прослушанных треков
             select msg from statistics where code = 30 and user_id = %s order by id DESC; 
             """ % user_id)


            tracks_listened_today = await scalar(db, """
             -- получить кол-во прослушанных треков
             select count(id) from statistics where code = 30 and user_id = %s 
             and (created_at between date_trunc('day', now()) and now() ) ; 
             """ % user_id)

            tags_seted_today = await  scalar(db, """
            -- получить кол-во тегов проставлено за сегодня
            select count(id) from statistics where code = 5 and user_id = %s and (created_at between date_trunc('day', now()) and now() ); 

            """ % user_id)

            tags_seted = await scalar(db, """
            -- получить кол-во тегов проставлено 
            select count(id) from statistics where code = 5  and user_id = %s ; 

            """ % user_id)

            tags_unseted_today = await scalar(db, """
            -- получить кол-во тегов снято за сегодня
            select count(id) from statistics where code = 6 and user_id = %s and (created_at between date_trunc('day', now()) and now() ); 

            """  % user_id )

            tags_unseted = await scalar(db, """
            -- получить кол-во тегов снято за сегодня
            select count(id) from statistics where code = 6 and user_id = %s; 

            """  % user_id )


            return web.json_response({
                'id': user_id,
                'group': group,
                'tracks_listened': tracks_listened,
                'tracks_listened_today' : tracks_listened_today,
                'tags_seted_today' : tags_seted_today,
                'tags_seted' : tags_seted,
                'tags_unseted_today' : tags_unseted_today,
                'tags_unseted' : tags_unseted,
                'tracks_listened_last' : tracks_listened_last
            })
