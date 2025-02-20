import re
from datetime import datetime as dt

async def is_int(val):
    try:
        num = int(val)
        return True
    except (TypeError, ValueError):
        return False

async def is_valid_date(date_str):
    # Проверяем, что строка соответствует формату дд.мм.гггг
    date_pattern = r"^\d{2}\.\d{2}(\.\d{4})?$"
    if not re.match(date_pattern, date_str):
        return False

    # Преобразуем строку в объект datetime и проверяем на валидность
    try:
        # 2 символа число, 2 месяц, 4 год и 2 точки = 10
        pattern = "%d.%m.%Y" if len(date_str) == 10 else "%d.%m"
        dt.strptime(date_str, pattern)
        return True
    except ValueError:
        return False


#   "chat_id" : [ {...}, {...} ]
async def convert_tuple_to_dict_with_custom_columns(query: list[tuple], columns: list[str], key_index: int) -> dict[str, list[dict]]:
    grouped = {}
    for row in query:
        key = row[key_index]
        if key not in grouped:
            grouped[key] = list()
        grouped[key].append(dict(zip(columns, row)))
    return grouped

async def generate_own_birth_dates_info(grouped: dict[str, list[dict]]) -> str:
    res = ''
    for month, itms in grouped.items():
        res += f'Месяц: {month}\n'
        for item in itms:
            res += f"Дата: {item['day']}.{item['month']}" \
                   + (f'.{item["year"]}' if item["year"] != 'NULL' and '' else '') \
                   + f". Имя: {item['celebrant_name']}." + f' Id: {item["id"]} ' + '\n'
        res += '\n'

    return res

async def generate_next_30_days_info(arr: list[dict]) -> str:
    res: str = ''
    for item in arr:
        res += f"Дата: {item['nearest_date']}. Имя: {item['celebrant_name']}. Через: {int(item['days_until'])} дней\n"
    return res

