import asyncio
from datetime import datetime, timedelta

from telegram import Bot
from telegram.error import TimedOut, NetworkError, RetryAfter

from db.db_interact import save_notification, get_none_notified_birthdate_in_interval, get_missed_births, \
    fill_last_launch_log, DBService, get_db_instance, configure_db_instance

import logging

import os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv('TG_TOKEN')

async def send_notifications(db_instance: DBService, notifications: dict[str, list[dict]]):
    retries = 5
    delay = 2

    async with Bot(TOKEN) as bot:
        for chat_id, messages in notifications.items():
            for msg in messages:
                try:
                    for attempt in range(retries):
                        await bot.send_message(chat_id=chat_id, text=msg['message'])
                        await save_notification(db_instance=db_instance, date_of_birth_id=msg['date_of_birth_id'])
                        break
                except TimedOut as e:
                    print(f"Таймаут: {str(e)}")
                    await asyncio.sleep(delay)
                except NetworkError as e:
                    print(f"Ошибка сети: {str(e)}")
                    await asyncio.sleep(delay)
                except RetryAfter as e:
                    wait_time = e.retry_after
                    print(f"Превышен лимит запросов! Ждём {wait_time} сек")
                    await asyncio.sleep(wait_time)
                except Exception as e:
                    print(f"Неизвестная ошибка: {str(e)}")
                    break

#   "chat_id" : [ msg, msg ]
def generate_messages_per_user_id(grouped: dict[str, list[dict]]) -> dict[str, list[dict]]:
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

            if x['year'] != None and x['year'].lower() != 'null' and x['year'] != '':
                msg += f'{datetime.now().year - int(x["year"])}'
            else:
                msg += ' неизвестно'

            notifications[chat_id].append({"message": msg, "date_of_birth_id": x["date_of_birth_id"]})

    return notifications


async def process_birth_dates(db_instance: DBService, interval_from: int, interval_to: int) -> None:
    grouped = await get_none_notified_birthdate_in_interval(db_instance=db_instance, interval_from=interval_from, interval_to=interval_to)

    notifications = generate_messages_per_user_id(grouped)

    await send_notifications(db_instance=db_instance, notifications=notifications)


async def process_missed_birth_dates(db_instance: DBService):
    logging.info("Обработка пропущенных дат")

    grouped = await get_missed_births(db_instance=db_instance)
    missed = generate_missed_messages_per_user_id(grouped)
    await send_notifications(db_instance=db_instance, notifications=missed)


def generate_missed_messages_per_user_id(grouped):
    notifications = {}
    for chat_id, arr in grouped.items():
        if chat_id not in notifications:
            notifications[chat_id] = list()

        for x in arr:
            sub_msg = f"{x['celebrant_name']} {int(x['days_ago'])} дня назад ({x['date']})"
            msg = f'По техническим причинам было пропущено ДР:\n{sub_msg}'
            notifications[chat_id].append({"message": msg, "date_of_birth_id": x["date_of_birth_id"]})

    return notifications

async def process_all_intervals(db_instance: DBService):
    logging.info("Обработка наступающих дат")
    intervals = [[0, 0], [1, 3], [4, 7], [8, 14]]
    for interval in intervals:
        await process_birth_dates(db_instance=db_instance, interval_from=interval[0], interval_to=interval[1])


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
async def main():
    POSTGRES_USER = os.getenv('POSTGRES_USER')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
    POSTGRES_DB = os.getenv('POSTGRES_DB')
    OUTER_PORT = os.getenv('OUTER_PORT')
    INTERNAL_PORT = os.getenv('INTERNAL_PORT')
    POSTGRES_DB_SERVICE_NAME = os.getenv('POSTGRES_DB_SERVICE_NAME')

    configure_db_instance(INTERNAL_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB_SERVICE_NAME)
    db_instance = get_db_instance()


    await process_missed_birth_dates(db_instance=db_instance)


    await process_all_intervals(db_instance=db_instance)

    logging.info("Заполнение последнего успешного запуска")
    await fill_last_launch_log(db_instance=db_instance)

    now = datetime.now()
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    sec = int((next_hour - now).total_seconds())
    await asyncio.sleep(sec)



if __name__ == "__main__":
    asyncio.run(main())
