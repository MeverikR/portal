import xlsxwriter
from io import BytesIO
import dateutil.parser as date_parser


def make_report(reportData_: list, headFields: list, userFields: list, meta, hiders=None):
    reportData = reportData_.get('result').get('data')
    total = reportData_.get('result').get('metadata').get('total_items')
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('Звонки CoMagic')
    lost = workbook.add_format({
        'bg_color': '#ffdcc6',

    })
    h1 = workbook.add_format()
    h1.set_font_size(14)
    h1.set_font_color('gray')
    h1.set_bold()

    h2 = workbook.add_format()
    h2.set_font_size(16)
    h2.set_bold()

    h3 = workbook.add_format()
    h3.set_font_size(15)
    h3.set_bold()

    # заголовок

    __from = date_parser.parse(str(meta.get('from'))).strftime('%d-%m-%Y %H-%M-%S')
    __till = date_parser.parse(str(meta.get('till'))).strftime('%d-%m-%Y %H-%M-%S')
    worksheet.merge_range('B2:E2',
                          "Звонки за период с " + __from  + " " + __till , h2)
    worksheet.merge_range('B3:D3', "Клиент: " + str(meta.get('client')) + ". Аналитик: " + str(meta.get('user')) + ".",
                          h3)
    worksheet.merge_range('B4:D4', "Общее количество звонков в отчете: " + str(total), h3)

    row = 4
    col = 0
    # шапко
    _pattern = []  # складываем сюда коды полей по порядку
    tHead = []

    if hiders and bool(hiders.get('hide_sys_id')) is False:
        tHead.append(('ID обращения', 20))
        _pattern.append('communication_id')

    if hiders and bool(hiders.get('hide_sys_aon')) is False:
        tHead.append(('АОН', 22))
        _pattern.append('contact_phone_number')


    for fld in headFields:
        # FIXME: надо размер столбика грузить из конфига
        if fld.get('id') in userFields:
            _pattern.append(fld.get('id'))
            tHead.append((fld.get('name'), int(fld.get('size')) if fld.get('size') else 50))

    tHead.append(('Теги', 60))
    _pattern.append('tags')

    if hiders and bool(hiders.get('hide_sys_static')) is False:
        tHead.append(('Прослушан?', 60))
        _pattern.append('listened')

    if hiders and bool(hiders.get('hide_sys_player')) is False:
        tHead.append(('Ссылка на запись', 120))
        _pattern.append('call_records')

    # рендер шапки
    for th in tHead:
        worksheet.write(row, col, th[0], h1)
        worksheet.set_column(col, col, th[1])
        col += 1
    row += 1

    # рендер данных
    for line in reportData:
        col = 0
        for el in _pattern:
            data = line.get(el)
            if el == 'tags':
                if data:
                    _a_list = [d['tag_name'] for d in data if 'tag_name' in d and d is not None]
                    value = ", ".join(_a_list if _a_list else [])
                else:
                    value = ""
            elif el in ['wait_duration', 'total_wait_duration', 'talk_duration', 'clean_talk_duration', 'postprocess_duration']:
                import datetime
                value = str(datetime.timedelta(seconds=int(line.get(el, 0))))
            elif el == 'call_records':
                if data and len(data) > 0:
                    value = "https://app.comagic.ru/system/media/talk/%s/%s/" % (line.get('id'), data[0] )
                else:
                    value = 'нет записи'
            elif isinstance(line.get(el), dict):
                value = ", ".join(data.values() if data else [])
            elif isinstance(line.get(el), list):
                value = ", ".join(data if data else [])
            else:
                value = str(data if data else '')
            # пишем строчку
            if bool(line.get('is_lost')):
                worksheet.write(row, col, value if value else '', lost)
            else:
                worksheet.write(row, col, value if value else '')
            col += 1  # переключаем колонку
        row += 1  # увеличиваем строку

    row += 1
    col = 0

    workbook.close()
    output.seek(0)

    return output  # это в памяти файлец
