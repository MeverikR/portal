# language: ru
# Created by p.lobanov at 25.03.2019
Функционал: Работа с клиентами

  Система позволяет добавлять/удалять/редактировать клиентов
  Работать с клиентами может только суперадминистратор


#################
  Сценарий: Суперадминистратор получает список клиентов
    Пусть я логинюсь в слухачей как "superadmin" с паролем "sodmin25"
    Когда я запрашиваю "/clients?_end=10&_order=DESC&_sort=id&_start=0"
    Тогда код ответа сервера 200
    И в ответе присутствует JSON массив размером как минимум 2 элемента
###################
  Сценарий: Суперадминистратор заходит в систему и добавляет нового клиента
    Пусть я логинюсь в слухачей как "superadmin" с паролем "sodmin25"
    И тело запроса:
    """
    {
    "name":"TestToken",
    "token":"7mx5k98hp5oxg2d8jqa4vxkd8chbf5kh7ryigprm",
    "infopin":111,
    "app_id":222,
    "adm_login":"__test_token__",
    "adm_pass":"__test_token__",
    "adm_email":"__test__@example.com"
    }
    """
    Когда я запрашиваю "/clients" используя HTTP POST
    Тогда код ответа API 200
    И я проверил и сохранил юзера из ответа, должны быть такие данные:
    """
    {
      "id" :  "@gt(0)",
      "name" : "TestToken"
    }
    """
#########################
  Сценарий: Суперадмин редактирует данные добавленного клиента
    Пусть я логинюсь в слухачей как "superadmin" с паролем "sodmin25"
    И тело запроса:
    """
    {
    "name":"TestToken",
    "token":"7mx5k98hp5oxg2d8jqa4vxkd8chbf5kh7ryigprm",
    "infopin":555,
    "app_id":666

    }
    """
    Когда я обновляю ранее созданного клиента
    Тогда код ответа API 200
    И в ответе есть примерно такой JSON:
    """
    {
      "name" : "TestToken",
      "infopin" : 555,
      "app_id" : 666
    }
    """
#######################
  Сценарий: Входим под администратором свежесозданного клиента
    Пусть я логинюсь в слухачей как "__test_token__" с паролем "__test_token__"
    Когда я запрашиваю "/users?_end=10&_order=DESC&_sort=id&_start=0"
    То код ответа 200
###################
  Сценарий: Суперадминистратор удаляет клиента
    Пусть я логинюсь в слухачей как "superadmin" с паролем "sodmin25"
    Когда я удаляю клиента из предыдущего сценария
    Тогда код ответа 200
    И в ответе есть примерно такой JSON:
    """
    {
      "name" : "TestToken",
      "token" : "7mx5k98hp5oxg2d8jqa4vxkd8chbf5kh7ryigprm"
    }
    """
####################
  Сценарий: При попытке создать нового клиента с неправильно заполненным полем Токен всегда ошибка 406
    Пусть я логинюсь в слухачей как "superadmin" с паролем "sodmin25"
    И тело запроса:
    """
    {"name":"___TEST__CLIENT__ERR___","token":"__NOT_GOOD_TOKEN__","infopin":111,"app_id":111,"adm_login":"__adm__log__","adm_pass":"__adm__log__","adm_email":"__adm__log__@example.com"}
    """
    Когда я запрашиваю "/clients" используя HTTP POST
    Тогда код ответа сервера 406
    И причина в ответе соответствует условию "/access_token_blocked/i"
    Когда я запрашиваю "/clients" используя HTTP POST
    И причина в ответе соответствует условию "/access_token_blocked/i"
    Тогда код ответа сервера 406
####################
  Сценарий: попытка создать клиента с уже существующим токен всегда оборачивается ошибкой 406
    Пусть я логинюсь в слухачей как "superadmin" с паролем "sodmin25"
    И тело запроса:
    """
    {"name":"___TEST__CLIENT__ERR___","token":"ei2ckww3ngr8gkbsxqmw6m9wp5owq735vpx8f2hm","infopin":111,"app_id":111,"adm_login":"__adm__log__","adm_pass":"__adm__log__","adm_email":"__adm__log__@example.com"}
    """
    Когда я запрашиваю "/clients" используя HTTP POST
    Тогда код ответа сервера 406
    И причина в ответе соответствует условию "/token already exists/i"
    Когда я запрашиваю "/clients" используя HTTP POST
    Тогда код ответа сервера 406
    И причина в ответе соответствует условию "/token already exists/i"
######################
  Сценарий: создаем пользователей у клиента с типом администратор и типом слушатель
    Пусть я логинюсь в слухачей как "superadmin" с паролем "sodmin25"
    И тело запроса:
    """
    {
    "name":"TestToken",
    "token":"7mx5k98hp5oxg2d8jqa4vxkd8chbf5kh7ryigprm",
    "infopin":111,
    "app_id":222,
    "adm_login":"__test_token__",
    "adm_pass":"__test_token__",
    "adm_email":"__test__@example.com"
    }
    """
    Когда я запрашиваю "/clients" используя HTTP POST
    Тогда код ответа API 200
    И в ответе есть примерно такой JSON:
    """
    {
      "id" :  "@gt(0)",
      "name" : "TestToken"
    }
    """
    И сохранить из ответа JSON значение свойства "id" как "test_client_id"
    # входим как админ клиента
    Пусть я логинюсь в слухачей как "__test_token__" с паролем "__test_token__"
    И тело запроса:
    """
    {"name":"TempEvaluator","login":"__temp_employ__","password":"__temp_employ__","email_address":"temp_employ@example.com","group_id":"1"}
    """
    Когда я запрашиваю "/users" используя HTTP POST
    Тогда код ответа API 200
    И в ответе есть примерно такой JSON:
    """
    {
      "id" :  "@gt(0)",
      "name" : "TempEvaluator",
      "login" : "__temp_employ__"
    }
    """
    И сохранить из ответа JSON значение свойства "id" как "test_client_user_admin"
    # пробуем создать клиента с длинными текстами
    Пусть я логинюсь в слухачей как "__test_token__" с паролем "__test_token__"
    И тело запроса:
    """
    {
    "name":"Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam mauris felis, pharetra ac velit non, pellentesque vestibulum risus. Nunc tempor odio dignissim aliquam aliquet. Donec pellentesque orci eu augue vestibulum molestie. Sed a nisl tellus. Donec fermentum mi purus, vel tristique nunc laoreet volutpat. Morbi ipsum nibh, porta sed orci id, mollis mattis purus. Sed felis ligula, laoreet ac semper lobortis, eleifend eu nisl. Integer in maximus purus. Curabitur sollicitudin tempor ligula at sagittis. Suspendisse egestas odio turpis, laoreet imperdiet velit scelerisque at. Vestibulum euismod varius lacus, nec venenatis ante. Quisque tristique enim in dui auctor, vitae vehicula nulla dignissim. Maecenas lacinia ante id odio eleifend, in varius tellus laoreet. Aenean nibh nulla, viverra vel pulvinar nec, aliquet sed quam. Mauris elementum placerat ipsum eget consectetur.Morbi lorem nibh, fringilla et est ut, tincidunt accumsan velit. Praesent nibh sem, luctus sed feugiat non, egestas in sapien. Nulla suscipit, urna vitae laoreet vulputate, ipsum velit tempus nibh, sed bibendum leo ante sed eros. Nullam sodales, neque commodo ullamcorper fringilla, sapien nunc consectetur lorem, non vehicula elit leo non justo. Donec sit amet sapien purus. Etiam cursus molestie condimentum. Etiam dignissim odio sed elit pretium aliquam. Praesent justo eros, ullamcorper a auctor vel, sodales malesuada eros. Aliquam iaculis sodales odio, nec tincidunt ligula sodales et. Aliquam erat volutpat. Quisque elit orci, convallis sed nisl in, faucibus egestas nisi. Pellentesque eu iaculis purus. Sed a venenatis diam. Aenean tincidunt eleifend eleifend. Fusce et commodo turpis, nec pharetra magna.",
    "login":"Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam mauris felis, pharetra ac velit non, pellentesque vestibulum risus. Nunc tempor odio dignissim aliquam aliquet. Donec pellentesque orci eu augue vestibulum molestie. Sed a nisl tellus. Donec fermentum mi purus, vel tristique nunc laoreet volutpat. Morbi ipsum nibh, porta sed orci id, mollis mattis purus. Sed felis ligula, laoreet ac semper lobortis, eleifend eu nisl. Integer in maximus purus. Curabitur sollicitudin tempor ligula at sagittis. Suspendisse egestas odio turpis, laoreet imperdiet velit scelerisque at. Vestibulum euismod varius lacus, nec venenatis ante. Quisque tristique enim in dui auctor, vitae vehicula nulla dignissim. Maecenas lacinia ante id odio eleifend, in varius tellus laoreet. Aenean nibh nulla, viverra vel pulvinar nec, aliquet sed quam. Mauris elementum placerat ipsum eget consectetur.Morbi lorem nibh, fringilla et est ut, tincidunt accumsan velit. Praesent nibh sem, luctus sed feugiat non, egestas in sapien. Nulla suscipit, urna vitae laoreet vulputate, ipsum velit tempus nibh, sed bibendum leo ante sed eros. Nullam sodales, neque commodo ullamcorper fringilla, sapien nunc consectetur lorem, non vehicula elit leo non justo. Donec sit amet sapien purus. Etiam cursus molestie condimentum. Etiam dignissim odio sed elit pretium aliquam. Praesent justo eros, ullamcorper a auctor vel, sodales malesuada eros. Aliquam iaculis sodales odio, nec tincidunt ligula sodales et. Aliquam erat volutpat. Quisque elit orci, convallis sed nisl in, faucibus egestas nisi. Pellentesque eu iaculis purus. Sed a venenatis diam. Aenean tincidunt eleifend eleifend. Fusce et commodo turpis, nec pharetra magna.",
    "password":"Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam mauris felis, pharetra ac velit non, pellentesque vestibulum risus. Nunc tempor odio dignissim aliquam aliquet. Donec pellentesque orci eu augue vestibulum molestie. Sed a nisl tellus. Donec fermentum mi purus, vel tristique nunc laoreet volutpat. Morbi ipsum nibh, porta sed orci id, mollis mattis purus. Sed felis ligula, laoreet ac semper lobortis, eleifend eu nisl. Integer in maximus purus. Curabitur sollicitudin tempor ligula at sagittis. Suspendisse egestas odio turpis, laoreet imperdiet velit scelerisque at. Vestibulum euismod varius lacus, nec venenatis ante. Quisque tristique enim in dui auctor, vitae vehicula nulla dignissim. Maecenas lacinia ante id odio eleifend, in varius tellus laoreet. Aenean nibh nulla, viverra vel pulvinar nec, aliquet sed quam. Mauris elementum placerat ipsum eget consectetur.Morbi lorem nibh, fringilla et est ut, tincidunt accumsan velit. Praesent nibh sem, luctus sed feugiat non, egestas in sapien. Nulla suscipit, urna vitae laoreet vulputate, ipsum velit tempus nibh, sed bibendum leo ante sed eros. Nullam sodales, neque commodo ullamcorper fringilla, sapien nunc consectetur lorem, non vehicula elit leo non justo. Donec sit amet sapien purus. Etiam cursus molestie condimentum. Etiam dignissim odio sed elit pretium aliquam. Praesent justo eros, ullamcorper a auctor vel, sodales malesuada eros. Aliquam iaculis sodales odio, nec tincidunt ligula sodales et. Aliquam erat volutpat. Quisque elit orci, convallis sed nisl in, faucibus egestas nisi. Pellentesque eu iaculis purus. Sed a venenatis diam. Aenean tincidunt eleifend eleifend. Fusce et commodo turpis, nec pharetra magna.",
    "email_address":"temp_employ@example.com",
    "group_id":"1"}
    """
    Когда я запрашиваю "/users" используя HTTP POST
    Тогда код ответа API 400

    # входим под этим созданным клиентом
    Пусть я логинюсь в слухачей как "__temp_employ__" с паролем "__temp_employ__"
    И тело запроса:
    """
    {"name":"TempSluhach","login":"__temp_sluhach__","password":"__temp_sluhach__","email_address":"__temp_sluhach__@example.com","group_id":"2"}
    """
    Когда я запрашиваю "/users" используя HTTP POST
    Тогда код ответа 200
    И в ответе есть примерно такой JSON:
    """
    {
      "id" :  "@gt(0)",
      "name" : "TempSluhach",
      "login" : "__temp_sluhach__"
    }
    """
    И сохранить из ответа JSON значение свойства "id" как "test_client_user_sluhach"
    # и наконец входим под слухачем
    Пусть я логинюсь в слухачей как "__temp_sluhach__" с паролем "__temp_sluhach__"
    Когда я запрашиваю "/reports?_end=10&_order=DESC&_sort=id&_start=0"
    Тогда код ответа 200
    И в ответе присутствует JSON массив размером как минимум 1 элемент
    # ну и теперь удаляем клиента, он должен удалить всех юзеров
    Пусть я логинюсь в слухачей как "superadmin" с паролем "sodmin25"
    Когда я запрашиваю "/clients/<<test_client_id>>" используя HTTP DELETE
    Тогда код ответа 200
    И в ответе есть примерно такой JSON:
    """
    {
      "name" : "TestToken",
      "token" : "7mx5k98hp5oxg2d8jqa4vxkd8chbf5kh7ryigprm"
    }
    """
    И почистить временные файлы


  Сценарий: Суперадминистратор заходит в систему и добавляет нового клиента c НЕВАЛИДНЫМИ параметрами
    Пусть я логинюсь в слухачей как "superadmin" с паролем "sodmin25"
    И тело запроса:
    """
    {
    "name":"TestToken",
    "token":"7mx5k98hp5oxg2d8jqa4vxkd8chbf5kh7ryigprm",
    "infopin":"sfdfsdfsdf",
    "app_id":"sdfsdf",
    "adm_login":"__test_token__",
    "adm_pass":"__test_token__",
    "adm_email":"__test__@example.com"
    }
    """
    Когда я запрашиваю "/clients" используя HTTP POST
    Тогда код ответа API 400

  Сценарий: Суперадминистратор заходит в систему и добавляет нового клиента, а потом обновляет его с НЕВАЛИДНЫМИ параметрами
    Пусть я логинюсь в слухачей как "superadmin" с паролем "sodmin25"
    И тело запроса:
    """
      {
      "id":1,
      "name":"",
      "infopin":183510,
      "app_id":223,
      "token":"ei2ckww3ngr8gkbsxqmw6m9wp5owq735vpx8f2hm",
      "admin":0,
      "created_at":"2019-02-21T14:05:44.844000",
      "updated_at":"2019-03-27T17:07:08.665153",
      "main_user":{
                  "id":1,
                  "name":"Админ тестового клиента",
                  "login":"admin_test",
                  "password":"test",
                  "email_address":"test@test.ru",
                  "group_id":1,
                  "client_id":1,
                  "comment":"Добавляет пользователей слухачей для тестовго клиента",
                  "created_at":"2019-02-21T14:09:26.494000",
                  "updated_at":"2019-03-27T17:07:08.467421"
                  },
       "users":{
            "count":15
            }
       }
    """
    Когда я запрашиваю "/clients/1" используя HTTP PUT
    Тогда код ответа API 400
    Пусть я логинюсь в слухачей как "superadmin" с паролем "sodmin25"
    И тело запроса:
    """
      {
      "id":1,
      "name":"Тестовый кабинет",
      "infopin":183510,
      "app_id":223,
      "token":"ei2ckww3ngr8gkbsxqmw6m9wp5owq735vpx8f2hm",
      "admin":1,
      "created_at":"2019-02-21T14:05:44.844000",
      "updated_at":"2019-03-27T17:07:08.665153",
      "main_user":{
                  "id":1,
                  "name":"",
                  "login":"admin_test",
                  "password":0,
                  "email_address":"test@test.ru",
                  "group_id":1,
                  "client_id":1,
                  "comment":"Добавляет пользователей слухачей для тестовго клиента",
                  "created_at":"2019-02-21T14:09:26.494000",
                  "updated_at":"2019-03-27T17:07:08.467421"
                  },
       "users":{
            "count":15
            }
       }
    """
    Когда я запрашиваю "/clients/1" используя HTTP PUT
    Тогда код ответа API 400
    Пусть я логинюсь в слухачей как "superadmin" с паролем "sodmin25"
    И тело запроса:
    """
      {
      "id":0,
      "name":"Тестовый кабинет",
      "infopin":183510,
      "app_id":223,
      "token":"ei2ckww3ngr8gkbsxqmw6m9wp5owq735vpx8f2hm",
      "admin":1,
      "created_at":"2019-02-21T14:05:44.844000",
      "updated_at":"2019-03-27T17:07:08.665153",
      "main_user":{
                  "id":1,
                  "name":"",
                  "login":"admin_test",
                  "password":0,
                  "email_address":"test@test.ru",
                  "group_id":1,
                  "client_id":1,
                  "comment":"Добавляет пользователей слухачей для тестовго клиента",
                  "created_at":"2019-02-21T14:09:26.494000",
                  "updated_at":"2019-03-27T17:07:08.467421"
                  },
       "users":{
            "count":15
            }
       }
    """
    Когда я запрашиваю "/clients/1" используя HTTP PUT
    Тогда код ответа API 400





















