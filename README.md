# Альтернативный личный кабинет аудио-аналитика

**Предпосылки к разработке**

*user story*

Я как руководитель отдела маркетинга оцениваю качество обращений с помощью сторонней компании,
сотрудники которой слушают звонки и присваивают им определенные теги по заданному правилу. 
При этом доступа к определенным звонкам, тегам и ни в какие другие разделы ЛК эти сотрудники иметь не должны.

*user case*

Я хочу чтобы слухачи имели доступ только к звонкам по сценариям "отдел продаж2,
отдел продаж4 и отдел продаж Химки", так как только звонки в отделы продаж должны быть оценены слухачами.
Оценка осуществляется с помощью тегирования, поэтому у слухачей должен быть доступ только к тегам, 
связанных с этим процессам, а именно : "целевой звонок", "нецелевой звонок", "1 комната", "2 комнаты", "3 комнаты",
 "брокер не взял трубку", "парковка". Именно на основании этих тегов мы определяем качество обращений.

**Функциональные требования**

Должен представлять из себя аналог отчета “список обращений - звонки” с ограниченным набором данных и контролов.

**Реализованный функционал**
- управление пользователями
- отдельные интерфейсы для каждого типа пользователей
- аналог отчета "список обращений - звонки" с возможностью ограничить список отображаемых полей
- возможность прослушивания звонков
- возможность устанавливать ограниченный набор тегов на обращение
- учет статистики установки/снятия тегов, прослушивания звонков
- разделение прав доступа
- быстрый экспорт отчета в XLS
 
**Скриншоты интерфейса**

- Форма входа в систему
![Форма входа в систему](https://monosnap.com/image/j284jLlEuLe71gkB3BKyyX0HEyxZJx.png)

- Интерфейс администратора клиента 
![Интерфейс администратора клиента](https://monosnap.com/image/PanqvSW7lsn7Bjd4AwIIN7UyPD48IU.png)



 

## Введение

Первая версия решения была создана на основе фреймворка Silex (PHP 5.6), который перешел в статус *deprecated* в июне 2018. 

Так, как поддерживать решение на php стало сложно - было принято решение переписать проект на более современные технологии.

Проект представляет собой систему, реализующую альтернативный личный кабинет клиента: аутентификация пользователя, авторизация пользователя, загрузка данных через серверный API. 

- серверная часть: aiohttp server реализующий собственный API для работы с клиентами и данными звонков из CoMagic
- клиентская часть: UI на основе фреймворка react-admin + react MUI (React JS)

## Структура проекта

```shell
.
├── client (клиентская часть - UI)
│   ├── build (скомпилированный клиент)
│   ├── node_modules (javascript модули и зависимости)
│   ├── public (boilerplate для запуска приложения react)
│   └── src (весь код клиентской части)
├── config (файлы конфигураций)
├── server (серверная часть - API)
│   ├── handlers (обработчики маршрутов/роутов URL)
│   └── helpers (вспомогательные классы и методы)
└── tests (поведенческие тесты на фреймворке Behat)
    ├── features (код тестов)
    ├── imbo_patch (патч зависимостей для быстрого развертывания)
    └── vendor (зависимости фреймворка Behat)

```

## Системные требования к серверу 

- Python >= 3.6
- Nodejs >= 6.14.3
- npm >= 3.10.10
- pip >= 19.0.1
- pipenv >= 2018.11.26
- nginx >= 1.10.1
- PostgreSQL >= 10
- Redis >= 3.2.12
- SSL (https)
- PHP >= 7.2 *
- composer >= 1.8.0 *

*для запуска поведенческих тестов из папки `tests` 
