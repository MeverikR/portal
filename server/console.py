#!python
# -*- coding: utf-8 -*-

"""
Модуль серверной консоли. Запускается из консоли вручную
Нужен для тестирования, отладки и мониторинга различных процессов на сервере
Например, эта штука может почистить/прогреть кеш, отправить письмо, сделать запрос, etc...
"""
import click

import asyncio
from functools import update_wrapper
from pprint import pprint


def coro(f):
    f = asyncio.coroutine(f)

    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(f(*args, **kwargs))

    return update_wrapper(wrapper, f)


greet = '## =========== %s версия %s КОНСОЛЬ ОТЛАДКИ =========== ##'


@click.group()
def cli():
    """
    Данная утилита представляет собой простой инструмент мониторинга и тестирования
    различных серверных задач.
    Например, эта штука может почистить/прогреть кеш, отправить письмо, сделать запрос, etc...
    В общем список комманд с описанием вы видите ниже
    """
    from helpers.config import Config
    serv_config = Config.get_config()
    click.echo(
        click.style(
            greet % (
                serv_config.get('app').get('name'),
                serv_config.get('app').get('ver')
            ), bg='blue', fg='white'))


@cli.command()
def test_server():
    """
    Позволяет проверить запущен сервер или нет.
    Также проверяет доступ к маршруту check_health минуя nginx.

    """
    pass


@cli.command()
@coro
async def test_redis():
    """
    Проверка редиса
    :return:
    """
    from aiocache import caches
    from helpers.config import Config
    serv_config = Config.get_config()
    cache_conf = serv_config.get('redis')
    caches.set_config({
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
    cache = caches.get('default')
    await cache.set('test_a_list', [1,2,3,4,5])
    await cache.set('test_b_list', ['1', '2', '3', '4', '5'])
    a = await cache.get('test_a_list')
    b = await cache.get('test_b_list')
    pprint(a[:2])
    pprint(b[3:])
    print('ok')


@cli.command()
def list_models():
    """
    Получить список моделей
    :return:
    """
    from helpers import db
    tabs = db.get_models()
    click.echo(click.style('Доступные таблицы', fg='green'))
    print(tabs)


@cli.command()
@coro
async def list_users():
    """
    Показать пользователей
    """
    from helpers import db
    from helpers.config import Config
    from helpers.models.users import User

    c = Config.get_config()
    click.echo(click.style(str(User.get(100, 0, 'id', 'DESC')), fg='green'))
    if 'postgres' not in c:
        click.echo(click.style('Config error. Cant load DB postgres', fg='red'))
    # получаем драйвер БД по конфигу
    pg = await db.get_pg_engine(c.get('postgres'))
    click.echo(await db.many(pg, User.get(100, 0, 'id', 'DESC')))


@cli.command()
@click.argument('user_id')
@coro
async def list_user_params(user_id):
    """
    Показать пользователей
    """
    from helpers import db
    from helpers.models.params import Param
    click.echo(click.style(str(Param.get_by([Param.user_id == user_id])), fg='green'))
    click.echo(await db.many(await db.autoconfig(),
                             Param.get_by([Param.user_id == user_id])
                             ))


@cli.command()
@click.argument('login')
@coro
async def get_by_login(login):
    """
    Показать пользователей
    """
    from helpers import db
    from helpers.models.users import User
    click.echo(click.style(str(User.get_by_login(login)), fg='green'))
    click.echo(await db.many(await db.autoconfig(),
                             User.get_by_login(login)
                             ))


@cli.command()
@click.argument('user_id')
@click.argument('token')
@coro
async def add_default_params(user_id, token):
    """
    Добавить дефолтные настройки юзеру
    """
    from helpers import db
    from helpers.config import Config
    from sqlalchemy.sql import text, select, func, and_
    from helpers.models.users import User
    from helpers.models.params import Param
    from helpers.dataprovider import DataProvider
    dp = DataProvider(token)
    # задаем теги пользователя
    tags = await dp.get_tags()
    _tags = []
    for tag in tags:
        _tags.append(tag.get('id'))

    data = {
        'fields': dp.get_fields(),
        'filters': [],
        'tags': _tags,
        'allow_tags_add': True,
        'allow_tags_delete': True,
        'user_id': user_id,

    }
    click.echo(click.style(str(data), fg='green'))
    click.echo(click.style(str(Param.add(data)), fg='green'))

    c = Config.get_config()
    if 'postgres' not in c:
        click.echo(click.style('Config error. Cant load DB postgres', fg='red'))
    # получаем драйвер БД по конфигу
    pg = await db.get_pg_engine(c.get('postgres'))
    click.echo(await db.many(pg, Param.add(data)))


@cli.command()
@click.argument('id')
@coro
async def show_user(id):
    """
    Показать пользователя
    """
    from helpers import db
    from helpers.config import Config
    from sqlalchemy.sql import text, select, func, and_
    from helpers.models.users import User
    from helpers.models.params import Param

    c = Config.get_config()
    if 'postgres' not in c:
        click.echo(click.style('Config error. Cant load DB postgres', fg='red'))
    # получаем драйвер БД по конфигу
    db_pg = await db.get_pg_engine(c.get('postgres'))
    async with db_pg.acquire() as conn:
        result = await conn.execute(
            User.get_by_id(id)
        )
        rowcount = result.rowcount
        users = await result.fetchone()
    click.echo(dict(users))


@cli.command()
@click.argument('row_id')
@coro
async def del_static(row_id):
    from helpers import db
    from helpers.models.log import Statistic
    click.echo(click.style(
        str(Statistic.remove([Statistic.id == row_id, Statistic.id > 0]))
        , fg='green'))

    click.echo(await db.delete(await db.autoconfig(),
                               Statistic.remove([Statistic.id == row_id, Statistic.id > 0])))



@cli.command()
@click.argument('user_id')
@coro
async def show_user_full(user_id):
    """
    Показать пользователя с настройками
    """
    from helpers import db
    from helpers.models.users import User
    from helpers.models.params import Param

    click.echo(click.style(
        str(User.join(Param, 1, 0, where_=[User.id == user_id],
                      on=User.id == Param.user_id))
        , fg='green'))
    click.echo(await db.many(await db.autoconfig(),
                             User.join(Param, 1, 0, where_=[User.id == user_id],
                                       on=User.id == Param.user_id)
                             ))


@cli.command()
@click.argument('user_id')
@click.argument('param')
@click.argument('to_value')
@coro
async def change_user_param(user_id, param, to_value):
    """
    Поменять настройки у юзера
    """
    from helpers import db
    from helpers.models.users import User
    from helpers.models.params import Param

    click.echo(click.style(
        str(User.update(
            {str(param): str(to_value)},
            [User.id == user_id]
        )
        )
        , fg='green'))
    click.echo(await db.update(await db.autoconfig(),
                            User.update(
                                {str(param): str(to_value)},
                                [User.id == user_id]
                            )
     ))


@cli.command()
@click.argument('group_id')
@coro
async def get_group(group_id):
    """
    Показать пользователя с настройками
    """
    from helpers import db
    from helpers.models.users import User
    from helpers.models.groups import Group

    click.echo(
        click.style(
            str(Group.get(limit_=100, offset_=0, where_=[Group.id == group_id, Group.id > 0])),
            fg='green'
        )
    )
    click.echo(await db.many(await db.autoconfig(),
                             Group.get(limit_=100, offset_=0, where_=[Group.id == group_id, Group.id > 0])
                             ))


@cli.command()
@click.argument('client_id')
@coro
async def get_client_users(client_id):
    from helpers import db
    from helpers.models.users import User
    click.echo(
        click.style(
            str(User.get_count(where_=[User.client_id == client_id])),
            fg='green'
        )
    )
    click.echo(await db.scalar(await db.autoconfig(),
                               User.get_count(where_=[User.client_id == client_id])
                            ))



@cli.command()
@click.argument('user_login')
@click.argument('user_password')
@coro
async def check_user_login(user_login, user_password):
    from helpers import db
    from helpers.models.users import User
    from helpers.models.groups import Group

    click.echo(
        click.style(
            str(User.get(
                1, 0, where_=[User.login == user_login, User.password == user_password]
            )),
            fg='green'
        )
    )
    click.echo(await db.many(await db.autoconfig(),
                            User.get(
                                1, 0, where_=[User.login == user_login, User.password == user_password]
                            )
                            ))

@cli.command()
@click.argument('text')
@coro
async def test_error_send(text):
    from helpers.config import Config
    from helpers.mail import Mail
    import json
    c = Config.get_config()
    mail = Mail(**c['mail'])
    mail.init_error_mailer(**c['error_mailing'])
    res = mail.send_error(text)
    click.echo(click.style(json.dumps(res), fg='green'))



@cli.command()
@click.argument('user_login')
@coro
async def check_user(user_login):
    """
    Показать пользователя с настройками
    """
    from helpers import db
    from helpers.models.users import User

    click.echo(
        click.style(
            str(User.check_identity(user_login)),
            fg='green'
        )
    )
    click.echo(await db.many(await db.autoconfig(),
                             User.check_identity(user_login)
                             ))


@cli.command()
@click.argument('table')
@coro
async def drop_table(table):
    """
    Удаляет табличку
    :param table:
    :return:
    """
    from helpers import db
    from helpers.config import Config
    c = Config.get_config()
    if 'postgres' not in c:
        click.echo(click.style('Config error. Cant load DB postgres', fg='red'))
    # получаем драйвер БД по конфигу
    db_pg = await db.get_pg_engine(c.get('postgres'))
    tabs = db.get_models()
    if table not in tabs:
        click.echo(
            click.style('No model found with name %s use one of this: [%s]' % (table, ", ".join(tabs)), fg='red'))
    click.echo(click.style('Droppping table [%s] please wait...' % table, fg='yellow'))
    if await db.drop_table(db_pg, table):
        click.echo(click.style('DONE DROP table [%s]' % table, fg='green', bg='white'))


@cli.command()
@click.argument('table')
@coro
async def create_table(table):
    """
    Создаем/пересоздаем табличку в бд
    :param table:
    :return:
    """
    from helpers import db
    from helpers.config import Config
    c = Config.get_config()
    if 'postgres' not in c:
        click.echo(click.style('Config error. Cant load DB postgres', fg='red'))
    # получаем драйвер БД по конфигу
    db_pg = await db.get_pg_engine(c.get('postgres'))
    tabs = db.get_models()
    if table not in tabs:
        click.echo(
            click.style('No model found with name %s use one of this: [%s]' % (table, ", ".join(tabs)), fg='red'))
    click.echo(click.style('Creating table [%s] please wait...' % table, fg='yellow'))
    if await db.create_table(db_pg, table):
        click.echo(click.style('DONE table [%s]' % table, fg='green', bg='white'))


@cli.command()
@click.argument('token')
def get_fields(token):
    click.echo('Список полей доступных в системе')
    from helpers.dataprovider import DataProvider
    dp = DataProvider(token)

    click.echo(dp.get_fields())


@cli.command()
@click.argument('token')
@coro
async def get_tags(token):
    click.echo('Попытка выполнить запрос в CoMagic - получаем список тегов доступных пользователю')
    from helpers.dataprovider import DataProvider
    dp = DataProvider(token)
    res = await dp.get_user_tags()
    click.echo(res)


@cli.command()
@click.argument('token')
@click.argument('date_from')
@click.argument('date_till')
@coro
async def data_api_test(token, date_from, date_till):
    """
    Делаем тестовый запрос к DataAPI
    """
    import time

    t = time.process_time()
    click.echo('Попытка выполнить запрос в CoMagic - получаем список звонков за период')
    click.echo(click.style('Token: %s' % token, fg='red'))

    from helpers.dataprovider import DataProvider
    dp = DataProvider(token)
    dp.set_period(date_from, date_till)
    res = await dp.get()
    tot = dp.get_total()
    _tot = len(res['result']['data'])
    period = dp.get_formated_period()
    elapsed_time = time.process_time() - t
    from helpers.utils import display_time

    click.echo('=======================')

    click.echo(click.style('Всего в мете: %d' % tot, fg='green', bg='white'))
    click.echo(click.style('Всего по факту: %d' % _tot, fg='green', bg='white'))
    click.echo(
        click.style('Период: с %s по %s' % (period.get('date_from'), period.get('date_till')), fg='green', bg='white'))
    click.echo('=======================')
    click.echo(click.style('Потрачено времени: %s' % display_time(elapsed_time), fg='red', bg='white'))


if __name__ == '__main__':
    cli(obj={})
