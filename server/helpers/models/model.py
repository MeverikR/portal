# чтоб 10 раз не писать методы генераторы кода
# тупо пронаследуем каждую модель от базовой
# в базовой один раз опишем мегагенераторызапросов

from sqlalchemy.sql import text, select, func, and_, desc, asc

class BaseModelMixin:
    """
    Я базовая модель 
    Пронаследуй свою от меня!
    """

#мегазапросогенераторы!

    @classmethod
    def get_by_id(self, uid):
        """
        Отдать по id
        """
        return select([self]).where(self.id == uid)


    @classmethod
    def get_count(self, where_):
        """
        Отдать по id
        """
        _select_ = select([func.count()]).select_from(self.__table__)

        for k in where_:
            _select_ = _select_.where(k)

        return _select_


    @classmethod
    def get_by_id_in(self, ids: list, where_: list = None):
        """
        Отдать по id
        """
        if where_:
            if len(where_) == 1:
                _select_ = select([self]).where(and_(where_[0],self.id.in_(ids)))
            else:
                _select_ = select([self]).where(and_(*where_,self.id.in_(ids)))
        else:
            return select([self]).where(self.id.in_(ids))

        print(_select_)
        return _select_


    @classmethod
    def get_by(self, where_: list):
        """
        Отдать по id
        """
        _select_ = select([self])

        for k in where_:
            _select_ = _select_.where(k)

        return _select_

    @classmethod
    def get(self, limit_, offset_, sort_ = None, order_ = None, where_: list = None):
        """
        Отдать много
        """

        if not sort_:
            sort_ = self.id

        if order_ == 'DESC':
            order = desc(sort_)
        else:
            order = asc(sort_)

        _select_ = select([self])

        if where_:
            if len(where_) == 1:
                _select_ = _select_.where(where_[0])
            else:
                _select_ = _select_.where(and_(*where_))

        return _select_.order_by(order).limit(limit_).offset(offset_)

    @classmethod
    def update(self, what_: dict, where_: list):
        """
        Простой апдейт
        """

        what_['updated_at'] = func.now()
        if 'created_at' in what_:
            del what_['created_at']

        return self.__table__.update().where(where_[0] if len(where_) == 1 else and_(*where_)).values(what_) 

    @classmethod
    def join(self, model_, 
     limit_, offset_, sort_ = None, order_ = None, 
     on = None, fields_: list = None, where_: list = None):
        """
        Сджойнить и отдать много
        """
        if sort_:
            if order_ == 'DESC':
                order = desc(sort_)
            else:
                order = asc(sort_)
        else:
            order = asc(self.id)


        if fields_:
            _select_ = select( fields_)
        else:     
            _select_ = select([self, model_]).apply_labels()

        if where_:
            if len(where_) == 1:
                _select_ = _select_.where(where_[0])
            else:
                _select_ = _select_.where(and_(*where_))
   
        return _select_.select_from(self.__table__.join(model_, on)).order_by(order).limit(limit_).offset(offset_)



    @classmethod
    def add(self, some):
        """
        Положить
        """
        if 'created_at' not in some:
            some['created_at'] = func.now()
        if 'updated_at' not in some:
            some['updated_at'] = func.now()

        return self.__table__.insert().values(**some)

    @classmethod
    def remove(self, where_: list = None):
        """
        Запрос на удаление
        :param where_:
        :return:
        """
        deleter = self.__table__.delete()

        if len(where_) == 1:
            deleter  = deleter.where(where_[0])
        else:
            deleter = deleter.where(and_(*where_))

        return deleter
