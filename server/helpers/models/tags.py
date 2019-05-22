from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy as sa

__all__ = ('Tags',)

Base = declarative_base()

class Tags(Base):
    """
    Класс для таблицы тегов
    """
    __tablename__ = 'tags'
    # id
    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(sa.Integer)
    # Название тега
    name = sa.Column(sa.String(250))
    # description
    description = sa.Column(sa.String(250),  nullable=True)
    # cm_id
    cm_id = sa.Column(sa.Integer, nullable=True)
    # даты
    created_at = sa.Column(sa.DateTime)
    updated_at = sa.Column(sa.DateTime)