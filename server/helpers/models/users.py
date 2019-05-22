import sqlalchemy as sa
from helpers.models.model import BaseModelMixin
from helpers.models.params import Param
from helpers.models.clients import Client
from helpers.models.groups import Group
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import text, select, func, and_, desc, asc
Base = declarative_base()


__all__ = ('User', )


class User(Base, BaseModelMixin):
    """
    Модель пользователей
    """
    __tablename__ = 'users'
    # id
    id = sa.Column(sa.Integer, primary_key=True)
    # ФИО или название юзера
    name = sa.Column(sa.String(250))
    # TODO: потом надо будет не хранить пароли
    # hash = sa.Column(sa.String(256), unique=True)
    login = sa.Column(sa.String(50), unique=True)
    password = sa.Column(sa.String(50))
    email_address = sa.Column(sa.String(100), nullable=True)
    # ссылка на группы
    group_id = sa.Column(sa.Integer)
    # ссылка на таблицу клиентов, там ключи хранятсо
    client_id = sa.Column(sa.Integer)
    # comment
    comment = sa.Column(sa.Text, nullable=True)
    # даты
    created_at = sa.Column(sa.DateTime)
    updated_at = sa.Column(sa.DateTime)

    @classmethod
    def check_identity(self, login):
        """
        Проверить пользователя
        """
        return self.__table__.count().where(self.login == login)

    @classmethod
    def get_by_login(self, login):
        """
        Отдать по id
        """
        return self.__table__.select().where(self.login == login)

    @classmethod
    def get_full_in_ids(self, ids, client, where_: list = None):
        s = select(
            [self, Param, Client, Group]
            ).apply_labels().select_from(
                self.__table__.join(Param, Param.user_id == self.id
                ).join(
                    Client, Client.id == self.client_id
                    ).join(
                        Group, Group.id == self.group_id)
                        ).where(
                            and_(self.id.in_(ids),
                             Client.id == client, *where_ or []))
        return s

    @classmethod
    def get_full(self, client, limit_, offset_, sort_, order_, where_: list):

        if order_ == 'DESC':
            order = desc(getattr(self, sort_))
        else:
            order = asc(getattr(self, sort_))

        s = select(
            [self, Param, Client, Group]
            ).apply_labels().select_from(
                self.__table__.join(Param, Param.user_id == self.id
                ).join(
                    Client, Client.id == self.client_id
                    ).join(
                        Group, Group.id == self.group_id)
                        ).where(
                            and_(Client.id == client, *where_ or [])
                            )

        return s.order_by(order).limit(limit_).offset(offset_)


    @classmethod
    def get_full_by_id(self, id, client, where_: list = None):

        s=select([self, Param, Client, Group]).apply_labels().select_from(self.__table__.join(Param, Param.user_id == id).join(
            Client, Client.id == self.client_id).join(Group, Group.id == self.group_id)).where(and_(self.id == id, Client.id == client, *where_ or []))
        return s


    @staticmethod
    def get_superadmin():
        import time
        date=time.strftime('%Y-%m-%d %H:%M:%S')

        return {
            'id': 0,
            'name': 'Суперадминистратор',
            'login': 'superadmin',
            'group_id': 0,
            'group': {'name': 'СуперАдминистратор', 'id': 0},
            'client_id': 0,
            'params': {
                'allow_tags_add': True,
                'allow_tags_delete': True,
                'hide_sys_id': False,
                'hide_sys_aon' : False,
                'hide_sys_player' : False,
                'hide_sys_static' : False,
                'enable_deleted_tags_check' : False
            },
            'client': {'name': '--- корневой пользователь ---'},
            'comment': 'суперадминистратор - может все',
            'created_at': date,
            'updated_at': date,
        }
