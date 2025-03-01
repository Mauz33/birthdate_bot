from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from db_interact import reg_user, get_births_by_chat_id, delete_birth_row, check_is_user_own_row, add_birth, \
    get_rows_the_next_n_days, \
    get_db_instance, DBService, get_none_notified_birthdate_in_interval
from key_boards import markup, cancel_markup
from notification_service import generate_messages_per_user_id, send_notifications
from utils import is_int, is_valid_date, generate_own_birth_dates_info, generate_next_30_days_info

MENU, INPUT_DATE, INPUT_CELEBRANT, CONFIRMATION, DELETE_BIRTH = range(5)

db_instance: DBService = get_db_instance()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reg_user(db_instance=db_instance, chat_id=update.message.chat.id)
    await update.message.reply_text("Начало работы.", reply_markup=markup)

    return MENU


async def show_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Панель управления.", reply_markup=markup)
    return MENU


async def delete_birth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Панель будет скрыта на время выполнения операции",
                                    reply_markup=ReplyKeyboardRemove())

    await update.message.reply_text("Введите ID записи для удаления", reply_markup=cancel_markup)

    return DELETE_BIRTH


async def execute_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    row_id = update.message.text
    chat_id = update.message.chat.id
    if not is_int(row_id):
        await update.message.reply_text("Неверный формат ID для удаления. Укажите целочисленный ID",
                                        reply_markup=cancel_markup)
        return DELETE_BIRTH

    if await check_is_user_own_row(db_instance=db_instance, chat_id=chat_id, row_id=int(row_id)):
        await delete_birth_row(db_instance=db_instance, row_id=int(row_id))
        await update.message.reply_text(f"Запись с ID {row_id} успешно удалена",
                                        reply_markup=markup)
    else:
        await update.message.reply_text(f"Запись с ID {row_id} не найдена или вы не являетесь её владельцем",
                                        reply_markup=cancel_markup)
        return DELETE_BIRTH

    return MENU


async def get_all_rows(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    grouped_rows = await get_births_by_chat_id(db_instance=db_instance, chat_id=update.message.chat.id)
    if len(grouped_rows) == 0:
        await update.message.reply_text("Список пуст")
        return MENU

    res = await generate_own_birth_dates_info(grouped=grouped_rows)

    await update.message.reply_text(res)
    return MENU


async def add_birth_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Панель будет скрыта на время выполнения операции",
                                    reply_markup=ReplyKeyboardRemove())

    await update.message.reply_text("Введите дату рождения в формате ДД.ММ или ДД.ММ.ГГГГ",
                                    reply_markup=cancel_markup)
    return INPUT_DATE


async def input_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    date = update.message.text
    if not is_valid_date(date):
        await update.message.reply_text(
            "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ или ДД.ММ.ГГГГ.",
            reply_markup=cancel_markup)
        return INPUT_DATE

    context.user_data["birth_date"] = date

    await update.message.reply_text("Укажите имя человека, которое будет отображаться в уведомлениях:",
                                    reply_markup=cancel_markup)
    return INPUT_CELEBRANT


async def input_celebrant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard_inline = [
        [InlineKeyboardButton(text="Да", callback_data="yes"), InlineKeyboardButton(text="Нет", callback_data="no")]
    ]
    inline_markup = InlineKeyboardMarkup(keyboard_inline)

    context.user_data["celebrant"] = update.message.text
    await update.message.reply_text(f"Сохранить запись?\n"
                                    f"Дата: {context.user_data['birth_date']}\n"
                                    f"Имя: {context.user_data['celebrant']} ",
                                    reply_markup=inline_markup)

    return CONFIRMATION


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    chat_id = query.message.chat.id
    date = context.user_data["birth_date"].split('.')
    res = date if len(date) == 3 else date + ["NULL"]
    birth_id = await add_birth(db_instance=db_instance, chat_id=chat_id, celebrant=context.user_data["celebrant"], date=res)

    intervals = [[0, 0], [1, 3], [4, 7], [8, 14]]
    for interval in intervals:
        res = await get_none_notified_birthdate_in_interval(db_instance=db_instance, interval_from=interval[0],
                                                                     interval_to=interval[1],
                                                                     birth_date_id=birth_id)
        if res:
            notifications = generate_messages_per_user_id(res)
            await send_notifications(db_instance=db_instance, notifications=notifications)
            break

    await query.answer()  # Закрываем всплывающее уведомление

    await query.edit_message_text("Запись сохранена. Используй /showpanel чтобы продолжить работу")

    context.user_data.clear()

    return ConversationHandler.END


async def deny(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()  # Закрываем всплывающее уведомление
    await query.edit_message_text("Запись отклонена. Используй /showpanel чтобы продолжить работу")

    context.user_data.clear()

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("Операция отменена. Используй /showpanel чтобы продолжить работу")

    return ConversationHandler.END


async def get_list_of_the_next_30_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id: int = update.message.chat.id
    arr: list[dict] = await get_rows_the_next_n_days(db_instance=db_instance, chat_id=chat_id, next_n_days=30)

    if len(arr) == 0:
        await update.message.reply_text("Список пуст")
        return MENU

    res = await generate_next_30_days_info(arr)

    await update.message.reply_text(res)
    return MENU
