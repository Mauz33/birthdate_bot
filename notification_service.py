import asyncio
from datetime import datetime
from config import TOKEN

from telegram import Bot

from db_interact import save_notification, get_none_notified_birthdate_in_interval, get_missed_births, \
    fill_last_launch_log

async def send_notifications(notifications: dict[str, list[dict]]):
    today = datetime.now().strftime("%Y-%m-%d")
    async with Bot(TOKEN) as bot:
        for chat_id, messages in notifications.items():
            for msg in messages:
                await bot.send_message(chat_id=chat_id, text=msg['message'])
                await save_notification(msg['date_of_birth_id'], today)

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

            if x['year'] != None and x['year'].lower != 'null' and x['year'] != '':
                msg += f'{datetime.now().year - int(x["year"])}'
            else:
                msg += ' неизвестно'

            notifications[chat_id].append({"message": msg, "date_of_birth_id": x["date_of_birth_id"]})

    return notifications



async def process_birth_dates(interval_from: int, interval_to: int) -> None:
    grouped = await get_none_notified_birthdate_in_interval(interval_from=interval_from, interval_to=interval_to)

    notifications = generate_messages_per_user_id(grouped)

    await send_notifications(notifications)


async def process_missed_birth_dates():
    grouped = await get_missed_births()
    missed = generate_missed_messages_per_user_id(grouped)
    await send_notifications(missed)


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

async def process_all_intervals():
    await process_birth_dates(8, 14)
    await process_birth_dates(4, 7)
    await process_birth_dates(1, 3)
    await process_birth_dates(0, 0)

async def main():
    await process_missed_birth_dates()

    await process_all_intervals()

    await fill_last_launch_log()


if __name__ == "__main__":
    asyncio.run(main())
