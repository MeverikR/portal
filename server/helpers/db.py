"""
Модуль для работы с БД
"""
import logging
from logging import config as logger_config
from aiopg.sa import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import CreateTable, DropTable
import psycopg2

from helpers.models.users import User
from helpers.models.clients import Client
from helpers.models.params import Param
from helpers.models.groups import Group
from helpers.models.log import Statistic

from helpers.config import Config
config = Config.get_config().get('postgres')

logger_config.dictConfig(Config.get_config().get('logging'))
logger = logging.getLogger()


# определим какие таблички будут в работе
# это ужасно убого, но как приготовить автоподгрузку я пока не знаю
tables = [
    User.__table__, Param.__table__,
     Client.__table__, Group.__table__,
    Statistic.__table__
     ]


Base = declarative_base()


async def autoconfig():
    return await get_pg_engine(config)

def get_models():
    """
    Получить список имен табличек
    :return:
    """
    ret = []
    for _ in tables:
        ret.append(_.name)
    return ret

############ для круда
# первым аргументом передаем энджин
# коряво но удоно ибо работает отовсюду


async def scalar(pg, query):
    """
    Получить одну колонку
    :param pg:
    :param query:
    :return:
    """
    logger.debug(query)
    async with pg.acquire() as conn:
        return await conn.scalar(query)

async def update(pg, query):
    """
    Обновить
    :param pg:
    :param query:
    :return:
    """
    logger.debug(query)
    async with pg.acquire() as conn:

        result = await conn.execute(
            query
            )
        return result.rowcount

async def delete(pg, query):
    logger.debug(query)
    async with pg.acquire() as conn:

        result = await conn.execute(
            query
            )

        return result.rowcount


async def insert(pg, query):
    """
    Вставить
    :param pg:
    :param query:
    :return:
    """
    logger.debug(query)
    async with pg.acquire() as conn:

        result = await conn.execute(
            query
            )

        return [dict(d) for d in result] or {}


async def one(pg, query):
    """
    Взять одну 
    """
    logger.debug(query)
    async with pg.acquire() as conn:
        result = await conn.execute(
            query        
            )
        rowcount = result.rowcount
        res = await result.fetchone()
        if res:
            return dict(res)
        else:
            return {}


async def many(pg, query):
    """
    Вытащить из базки много
    """
    logger.debug(query)
    async with pg.acquire() as conn:
        result = await conn.execute(
            query        
            )
        rowcount = result.rowcount
        res = await result.fetchall()
        return {'data': [dict(d) for d in res] or {}, 'total':rowcount or 0}

async def put(pg, query):
    """
    Вставка
    """
    logger.debug(query)
    async with pg.acquire() as conn:
        result = await conn.execute(
            query        
            )
        rowcount = result.rowcount or 0
        ids = result.inserted_primary_key or []
        
        return {'data': ids, 'total':rowcount}


async def create_tables(pg):
    async with pg.acquire() as conn:
        for table in tables:
            try:
                create_expr = CreateTable(table)
                await conn.execute(create_expr)
            except psycopg2.ProgrammingError as pe:
                # если таблички уже созданы будет ошибка
                print(str(pe))
                pass


async def create_table(pg, table):
    for _ in tables:
        if _.name == table:
            table = _
    async with pg.acquire() as conn:
        try:
            create_expr = CreateTable(table)

            await conn.execute(create_expr)
        except psycopg2.ProgrammingError as pe:
            # если таблички уже созданы будет ошибка
            print(str(pe))
            return False
        return True

async def drop_table(pg, table):
    for _ in tables:
        if _.name == table:
            table = _
    async with pg.acquire() as conn:
        try:
            create_expr = DropTable(table)
            await conn.execute(create_expr)
        except psycopg2.ProgrammingError as pe:
            # если таблички уже созданы будет ошибка
            print(str(pe))
            return False
        return True


async def get_pg_engine(config):
    return await create_engine(**config)

async def init_pg(app):
    engine = await create_engine(**config)

    async with engine.acquire() as conn:
        # создаем таблички, с игнором ошибок
        print('testing db timezone')
        print(await scalar(engine, "SELECT NOW()"))

        print('setting db timezone to Europe/Moscow')
        await conn.execute('SET TIMEZONE="Europe/Moscow"')
        # проверим время в базке, ибо с ним вообще ппц
        print('testing db time after')
        print(await scalar(engine, "SELECT NOW()"))

    await create_tables(engine)
    # сохраняем объект БД в глобальный объект приложения
    app['db'] = engine
   

async def close_pg(app):
    app['db'].close()
    await app['db'].wait_closed()
    del app['db']