from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy as sa
from helpers.models.model import BaseModelMixin

__all__ = ('Param',)

Base = declarative_base()

class Param(Base, BaseModelMixin):
    """
    Модель настроек пользователей
    Храним тут все что касается фильтров, полей тегов и др
    """
    __tablename__ = 'params'
    # id
    id = sa.Column(sa.Integer, primary_key=True)
    # поля в отчете у юзера fields : ['fasf', 'fsfsd']
    fields = sa.Column(sa.JSON)
    # фильтры для чувака прям кусок JSON с 'filters' : {''}
    filters = sa.Column(sa.JSON)
    # теги - список тегов, которые может пользователь видеть и проставлять
    tags = sa.Column(sa.JSON)
    # права на теги
    # разрешить добавлять новые произвольные теги
    allow_tags_add = sa.Column(sa.Boolean)
    # разрешить удалять теги, которые чувак видит
    allow_tags_delete = sa.Column(sa.Boolean)
    # Скрыть ID
    hide_sys_id = sa.Column(sa.Boolean)
    # Скрыть АОН
    hide_sys_aon = sa.Column(sa.Boolean)
    # Скрыть плеер
    hide_sys_player = sa.Column(sa.Boolean)
    # Скрыть статистику прослушивания в отчете 'Звонки'
    hide_sys_static = sa.Column(sa.Boolean)
    # Вкл. проверку удаленных тегов
    enable_deleted_tags_check = sa.Column(sa.Boolean)


    # id юзера - какому пользователю принадлежит данная настройка
    user_id = sa.Column(sa.Integer)
    # даты
    created_at = sa.Column(sa.DateTime)
    updated_at = sa.Column(sa.DateTime)
