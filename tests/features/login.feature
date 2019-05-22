# language: ru
Функционал: Логин пользователя

  Портал слухачей предполагает, что пользователь имеет один из 3х уровней доступа:
  суперадмин, админ, слухач. Чтобы реализовать данный ф-л сделали логин пользователя
  Пользователь видет окошко входа и логинется в систему со своим логином и паролем

  Итак пользователь должен нормально входить в свой профиль.
  Ему должен выдаваться токен, который храниться на клиенте в localStorage
  Должна быть ошибка, если логин пароль не верный

  Сценарий: Входим в систему как суперадмин
    Пусть тело запроса будет:
    """
    ewogICAgICAidXNlcm5hbWUiIDogInN1cGVyYWRtaW4iLAogICAgICAicGFzc3dvcmQiIDogInNvZG1pbjI1IgogICAgfQ==
    """
    Когда я запрашиваю "/login" используя HTTP POST
    Тогда код ответа сервера 200
    И в ответе содержится следующий JSON:
    """
    {
      "token" : "@variableType(string)",
      "user" : {
              "id" : 0,
              "group_id" : 0,
              "client_id" : 0,
              "login" : "superadmin",
               "params" : {
                  "allow_tags_add" : true,
                  "allow_tags_delete" : true,
                  "hide_sys_aon": false,
                  "hide_sys_id": false,
                  "hide_sys_player": false,
                  "hide_sys_static": false
                  }
               }
    }
    """

  Сценарий: Входим в систему как админ
    Пусть тело запроса будет:
    """
    ewoJInVzZXJuYW1lIiA6ICJhZG1pbl90ZXN0IiwKCSJwYXNzd29yZCIgOiAidGVzdCIKfQ==
    """
    Когда я запрашиваю "/login" используя HTTP POST
    Тогда код ответа API 200
    И в ответе содержится примерно такой JSON:
    """
    {
      "token" : "@variableType(string)",
      "user" : {
              "id" : 1,
              "group_id" : 1,
              "client_id" : 1,
              "login" : "admin_test"
              }

    }
    """


  Сценарий: Входим в систему как слухач
    Пусть тело запроса:
    """
    ewoJInVzZXJuYW1lIiA6ICJlcCIsCgkicGFzc3dvcmQiIDogImRzZnNkZiIKfQ==
    """
    Когда я запрашиваю "/login" используя HTTP POST
    Тогда код ответа 200
    И в ответе содержится примерно такой JSON:
    """
    {
      "token" : "@variableType(string)",
      "user" : {
              "id" : 29,
              "group_id" : 2,
              "client_id" : 1,
              "login" : "ep"
              }

    }
    """

# По задаче PRSL-1122
  Сценарий: Входим в систему как e_user1 слухач клиента Эста Александр Владимирович
    Пусть тело запроса:
    """
    eyJ1c2VybmFtZSIgOiAiZV91c2VyMSIsInBhc3N3b3JkIiA6ICJ4SzdwQ2lxIn0=
    """
    Когда я запрашиваю "/login" используя HTTP POST
    Тогда код ответа 200
    И в ответе содержится примерно такой JSON:
    """
    {
      "token" : "@variableType(string)",
      "user" : {
              "id" : 43,
              "group_id" : 2,
              "client_id" : 26,
              "login" : "e_user1"
              }

    }
    """
