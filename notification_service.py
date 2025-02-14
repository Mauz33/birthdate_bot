import asyncio
from datetime import datetime
import sqlite3
from time import strftime
from config import TOKEN

from telegram import Bot

connection = sqlite3.connect('database.db')
cursor = connection.cursor()

# TODO: когда поступает новая дата, то прогонять её сразу по всем диапазонам

columns_1 = ["date_of_birth_id", "chat_id", "celebrant_name", "day_month", "year", "nearest_date", "days_until"]


# TODO: обрабатывать таймаут, ошибку сети и только потом создавать notification
# TODO: перенести sql
async def send_notifications(notifications):
    today = datetime.now().strftime("%Y-%m-%d")
    async with Bot(TOKEN) as bot:
        for chat_id, messages in notifications.items():
            for msg in messages:
                await bot.send_message(chat_id=chat_id, text=msg['message'])
                cursor.execute(
                    f"""
                        insert into notified_birth_dates (date_of_birth_id, notify_date, is_missed)
                        values ({msg['date_of_birth_id']}, '{today}', {msg['is_missed']});
                    """
                )
                connection.commit()


async def sql_query(intervalFrom, intervalTo) -> list:
    query = cursor.execute(
        f"""
            select
            d.id,
            u.chat_id,
            d.celebrant_name,
            d.day || '.' || d.month as day_month,
            d.year,
            CASE WHEN julianday(DATE('now')) > julianday(strftime('%Y', 'now') || '-' || d.month || '-' || d.day)
                THEN strftime('%Y', 'now', '+1 years') || '-' || d.month || '-' || d.day
                ELSE strftime('%Y', 'now') || '-' || d.month || '-' || d.day
            END AS nearest_date,
            julianday(
                CASE WHEN julianday(DATE('now')) > julianday(strftime('%Y', 'now') || '-' || d.month || '-' || d.day)
                    THEN strftime('%Y', 'now', '+1 years') || '-' || d.month || '-' || d.day
                    ELSE strftime('%Y', 'now') || '-' || d.month || '-' || d.day
                END
            ) - julianday(date('now')) as days_until,
            max(nbd.notify_date)
            FROM date_of_births as d
            JOIN users u on u.id = d.user_id
            LEFT JOIN notified_birth_dates nbd on d.id = nbd.date_of_birth_id
            where julianday(nearest_date) - julianday(date('now')) BETWEEN {intervalFrom} AND {intervalTo}
              AND (nbd.notify_date is NULL OR (julianday(nearest_date) - julianday(
                    (select max(n.notify_date)
                     from notified_birth_dates as n
                     where n.date_of_birth_id = d.id)
                                                    )) NOT BETWEEN {intervalFrom} AND {intervalTo})
                                                    group by d.id;
            """
    ).fetchall()
    return query


#   "chat_id" : [ {...}, {...} ]
def convert_tuple_to_dict_with_custom_columns(query, columns) -> dict[str, list]:
    grouped = {}
    for row in query:
        chat_id = row[1]  # chat_id по индексу 1
        if chat_id not in grouped:
            grouped[chat_id] = list()
        grouped[chat_id].append(dict(zip(columns, row)))
    return grouped


#   "chat_id" : [ msg, msg ]
def generate_messages_per_user_id(grouped):
    notifications = {}
    for chat_id, arr in grouped.items():
        if chat_id not in notifications:
            notifications[chat_id] = list()
        for x in arr:
            if x['days_until'] == 0:
                sub_msg = 'Сегодня'
            else:
                sub_msg = f'Через {int(x["days_until"])} дней'
            msg = f'{sub_msg} ({x["day_month"]}) день рождения {x["celebrant_name"]}. Исполняется: '

            if x['year'] != None and x['year'].lower != 'null' and x['year'] != '':
                msg += f'{datetime.now().year - int(x["year"])}'
            else:
                msg += ' неизвестно'

            notifications[chat_id].append({"message": msg, "date_of_birth_id": x["date_of_birth_id"], "is_missed": 0})

    return notifications


def generate_missed_messages_per_user_id(grouped):
    notifications = {}
    for chat_id, arr in grouped.items():
        if chat_id not in notifications:
            notifications[chat_id] = list()

        for x in arr:
            sub_msg = f"{x['celebrant_name']} {int(x['days_ago'])} дня назад ({x['date']})"
            msg = f'По техническим причинам было пропущено ДР:\n{sub_msg}'
            notifications[chat_id].append({"message": msg, "date_of_birth_id": x["date_of_birth_id"], "is_missed": 1})

    return notifications


columns_2 = ["date_of_birth_id", "chat_id", "celebrant_name", "date", "days_ago"]

async def get_missed_births():
    query = cursor.execute("SELECT date(max(julianday(date))) from launch_logs").fetchone()
    last_launch = query[0]
    if not last_launch:
        last_launch = datetime.now().strftime("%Y-%m-%d")

    query = cursor.execute(
        f"""
        WITH dates AS (
        SELECT
            id,
            celebrant_name,
            day,
            month,
            julianday(date(printf('%d-%02d-%02d', strftime('%Y', '{last_launch}'), month, day))) AS bday_last_year,
            julianday(date(printf('%d-%02d-%02d', strftime('%Y', 'now'), month, day))) AS bday_this_year
        FROM date_of_births
        )

        SELECT d.id, u.chat_id, db.celebrant_name, date(bday_last_year) as date, julianday(date('now')) - bday_last_year AS days_ago
        FROM dates d
        LEFT JOIN notified_birth_dates nbd on nbd.date_of_birth_id = d.id
        JOIN date_of_births db on db.id = d.id
        JOIN main.users u on u.id = db.user_id
        WHERE bday_last_year > julianday('{last_launch}') AND bday_last_year < julianday(date('now')) AND is_missed is NULL

        UNION

        SELECT d.id, u.chat_id, db.celebrant_name, date(bday_this_year) as date, julianday(date('now')) - bday_this_year AS days_ago
        FROM dates d
        LEFT JOIN notified_birth_dates nbd on nbd.date_of_birth_id = d.id
        JOIN date_of_births db on db.id = d.id
        JOIN main.users u on u.id = db.user_id
        WHERE bday_this_year > julianday('{last_launch}') AND bday_this_year < julianday(date('now')) AND is_missed is NULL
        """).fetchall()

    grouped = convert_tuple_to_dict_with_custom_columns(query, columns_2)
    missed = generate_missed_messages_per_user_id(grouped)
    await send_notifications(missed)
    print('yh')

async def fill_last_launch_log():
    cursor.execute(
    f"""
    insert into launch_logs
    (date) 
    values ('{datetime.now().strftime("%Y-%m-%d")}');
    """, )
    connection.commit()


async def process_birth_dates(intervalFrom, intervalTo):
    query = await sql_query(intervalFrom, intervalTo)

    grouped = convert_tuple_to_dict_with_custom_columns(query, columns_1)

    notifications = generate_messages_per_user_id(grouped)

    await send_notifications(notifications)


async def main():
    await get_missed_births()

    await process_birth_dates(8, 14)
    await process_birth_dates(4, 7)
    await process_birth_dates(1, 3)
    await process_birth_dates(0, 0)

    await fill_last_launch_log()

asyncio.run(main())
