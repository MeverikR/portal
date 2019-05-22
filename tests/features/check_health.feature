# language: ru
Функционал: Тест состояния сервака. (/check_health)

  Чтобы убедится что сервак доступен и возвращает различные метрики

  Сценарий: Опрос состояния сервака
    Пусть я запрашиваю "/check_health" используя HTTP GET
    Тогда код ответа сервера 200
    И в ответе есть такой JSON:
    """
    {
    "jwt_issued_count": "@variableType(integer)",
    "crash_500": "@variableType(integer)",
    "data_api_failed_request_count": "@variableType(integer)",
    "data_api_added_tag_count": "@variableType(integer)",
    "listened_call_count": "@variableType(integer)"
    }
    """

  Сценарий: Неверные данные в роут check_health
    Пусть тело запроса будет:
    """
    Я злой хацкер шлю каку в роут чекхеалс слухачей
    """
    Когда я запрашиваю "/check_health" используя HTTP POST
    Тогда код ответа сервера 200
    И в ответе есть такой JSON:
    """
    {
      "jwt_issued_count" : "@variableType(integer)",
      "crash_500" : "@variableType(integer)",
      "data_api_failed_request_count" : "@variableType(integer)",
      "data_api_added_tag_count" : "@variableType(integer)",
      "listened_call_count" : "@variableType(integer)"
    }
    """

