import asyncio
from datetime import datetime
import sqlite3
from time import strftime

from telegram import Bot

connection = sqlite3.connect('database.db')
cursor = connection.cursor()

# TODO: когда поступает новая дата, то прогонять её сразу по всем диапазонам

columns = ["date_of_birth_id", "chat_id", "celebrant_name", "day_month", "nearest_date", "days_until"]


# TODO: обрабатывать таймаут, ошибку сети и только потом создавать notification
# TODO: перенести sql
async def send_notifications(notifications):
    today = datetime.now().strftime("%Y-%m-%d")
    async with Bot("TOKEN") as bot:
        for chat_id, messages in notifications.items():
            for msg in messages:
                await bot.send_message(chat_id=chat_id, text=msg['message'])
                cursor.execute(
                    f"""
                        insert into notified_birth_dates (date_of_birth_id, notify_date)
                        values ({msg['date_of_birth_id']}, '{today}');
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
            nbd.notify_date
            FROM date_of_births as d
            JOIN users u on u.id = d.user_id
            LEFT JOIN notified_birth_dates nbd on d.id = nbd.date_of_birth_id
            where julianday(nearest_date) - julianday(date('now')) BETWEEN {intervalFrom} AND {intervalTo}
              AND nbd.notify_date is NULL
               OR (julianday(nearest_date) - julianday(
                    (select max(n.notify_date)
                     from notified_birth_dates as n
                     where n.date_of_birth_id = d.id)
                                                    )) NOT BETWEEN {intervalFrom} AND {intervalTo};
            """
    ).fetchall()
    return query


#   "chat_id" : [ {...}, {...} ]
def convert_tuple_to_dict_with_custom_columns(query) -> dict[str, list]:
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
                sub_msg = f'Через {x["days_until"]} дней'
            msg = f'{sub_msg} ({x["day_month"]}) день рождения {x["celebrant_name"]}'

            notifications[chat_id].append({"message": msg, "date_of_birth_id": x["date_of_birth_id"]})

    return notifications


async def process_birth_dates(intervalFrom, intervalTo):
    query = await sql_query(intervalFrom, intervalTo)

    grouped = convert_tuple_to_dict_with_custom_columns(query)

    notifications = generate_messages_per_user_id(grouped)

    await send_notifications(notifications)


async def main():
    await process_birth_dates(8, 14)
    await process_birth_dates(4, 7)
    # await process_birth_dates(1, 3)
    # await process_birth_dates(0, 0)



asyncio.run(main())
