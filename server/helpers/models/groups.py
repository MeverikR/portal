from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy as sa
from helpers.models.model import BaseModelMixin

__all__ = ('Group',)

Base = declarative_base()

class Group(Base, BaseModelMixin):
    """
    Класс для таблицы тегов
    """
    __tablename__ = 'groups'
    # id
    id = sa.Column(sa.Integer, primary_key=True)

    # Название группы
    name = sa.Column(sa.String(250))
    # description
    description = sa.Column(sa.String(250),  nullable=True)
    # настройки доступа
    perms = sa.Column(sa.ARRAY(sa.String(250)), nullable=True)

    # даты
    created_at = sa.Column(sa.DateTime)
    updated_at = sa.Column(sa.DateTime)