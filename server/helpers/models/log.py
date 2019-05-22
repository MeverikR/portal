"""
Табличка статистики
"""
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy as sa
from helpers.models.model import BaseModelMixin

__all__ = ('Statistic',)

Base = declarative_base()

class Statistic(Base, BaseModelMixin):
    """
    Класс для таблицы логов
    Можно было б назвать его логом,
     но лог у нас это другое
    """
    __tablename__ = 'statistics'
    # id
    id = sa.Column(sa.Integer, primary_key=True)

    # user
    user_id = sa.Column(sa.Integer)
    # event code
    code = sa.Column(sa.Integer)
    # настройки доступа
    msg = sa.Column(sa.String)

    # даты
    created_at = sa.Column(sa.DateTime)
    updated_at = sa.Column(sa.DateTime)