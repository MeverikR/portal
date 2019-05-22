from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy as sa
from helpers.models.model import BaseModelMixin


__all__ = ('Client',)

Base = declarative_base()

class Client(Base, BaseModelMixin):
    """
    Модель клиенты
    """
    __tablename__ = 'clients'
    # id
    id = sa.Column(sa.Integer, primary_key=True)
    # Наименование организации
    name = sa.Column(sa.String(250))
    #
    infopin = sa.Column(sa.Integer, nullable=True)
    app_id = sa.Column(sa.Integer, nullable=True)
    token = sa.Column(sa.String(250), unique=True)
    # ссылка на основного пользователя
    admin = sa.Column(sa.Integer)

    # даты
    created_at = sa.Column(sa.DateTime)
    updated_at = sa.Column(sa.DateTime)