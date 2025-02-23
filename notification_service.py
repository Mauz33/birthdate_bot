import asyncio
from datetime import datetime
from config import TOKEN

from telegram import Bot

from db_interact import save_notification, get_none_notified_birthdate_in_interval, get_missed_births, \
    fill_last_launch_log, DBService, get_db_instance

async def send_notifications(db_instance: DBService, notifications: dict[str, list[dict]]):
    async with Bot(TOKEN) as bot:
        for chat_id, messages in notifications.items():
            for msg in messages:
                await bot.send_message(chat_id=chat_id, text=msg['message'])
                await save_notification(db_instance=db_instance, date_of_birth_id=msg['date_of_birth_id'])

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
    intervals = [[0, 0], [1, 3], [4, 7], [8, 14]]
    for interval in intervals:
        await process_birth_dates(db_instance=db_instance, interval_from=interval[0], interval_to=interval[1])


async def main():
    db_instance = get_db_instance()

    await process_missed_birth_dates(db_instance=db_instance)

    await process_all_intervals(db_instance=db_instance)

    await fill_last_launch_log(db_instance=db_instance)


if __name__ == "__main__":
    asyncio.run(main())
