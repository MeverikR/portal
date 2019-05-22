"""
Модуль с различными утилитками
которые как правило украдены со stack overflow и чутка переделаны :)
"""

from datetime import datetime
import json, jwt
__all__ = ('DateTimeAwareEncoder',)
class DateTimeAwareEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)


def display_time(seconds, granularity=2):
    """
    Секундны в нормальное время
    Нужно для отчета по звонкам
    """
    result = []
    intervals = (
        ('мес.', 2419200),  # 60 * 60 * 24 * 7 * 4
        ('нед.', 604800),  # 60 * 60 * 24 * 7
        ('д.', 86400),  # 60 * 60 * 24
        ('ч.', 3600),  # 60 * 60
        ('мин.', 60),
        ('сек.', 1),
    )

    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append("{} {}".format(value, name))
    return ', '.join(result[:granularity])


def group_from_labels(data: dict) -> dict:
    if 'group_id' in data and 'id' in data and 'client_id' in data:
        return data
    _user = {}
    _group = {}
    _param = {}
    _client = {}
    for k,v in data.items():
        if 'users_' in k:
            _user[str(k).replace('users_', '')] = v
        if 'params_' in k:
            _param[str(k).replace('params_', '')] = v
        if 'clients_' in k:
            _client[str(k).replace('clients_', '')] = v
        if 'groups_' in k:
            _group[str(k).replace('groups_', '')] = v
    _client.pop('token')
    _user['client'] = _client
    _user['group'] = _group
    _user['params'] = _param

    return _user
        
def group_from_labels_many(data: dict) -> dict:
    if 'group_id' in data and 'id' in data and 'client_id' in data:
        return data
    if 'data' not in data:
        return {}
    total = data.pop('total')    
    data = data.pop('data')
    all_users = []
    for u in data:
        _user = {}
        _group = {}
        _param = {}
        _client = {}
        for k,v in u.items():
            if 'users_' in k:
                _user[str(k).replace('users_', '')] = v
            if 'params_' in k:
                _param[str(k).replace('params_', '')] = v
            if 'clients_' in k:
                _client[str(k).replace('clients_', '')] = v
            if 'groups_' in k:
                _group[str(k).replace('groups_', '')] = v
        _client.pop('token')
        _user['client'] = _client
        _user['group'] = _group
        _user['params'] = _param
        all_users.append(_user)
    return {'data': all_users, 'total': str(total)}

    

def users_join_cleaner(data: dict) -> dict:
    """
    Переформатирует JSON после JOIN с юзерами
    :param data:
    :return:
    """
    new_data = {}
    group = data.pop('group')
    _user = {}
    _param = {}
    if 'group_id' in data and 'id' in data and 'client_id' in data:
        return data

    for k,v in data.items():
        if 'users_' in k:
            _user[str(k).replace('users_', '')] = v
        if 'params_' in k:
            _param[str(k).replace('params_', '')] = v

    new_data = _user
    new_data['params'] = _param
    new_data['group'] = group
    return new_data

def fields_preparator(fields):
    """
    Подготовим список полей из конфига
    в нормальный вид для JSON
    :param fields:
    :return:
    """
    json_fields = []
    for field in fields:
        json_fields.append({'id' : field.get('field'), 'name':field.get('label'),
                            '_type': field.get('type'), '_parent' : field.get('parent'), '_sort' : field.get('sort'),
                            'size' : field.get('size') if 'size' in field else ''
                            })
    return json_fields