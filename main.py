import asyncio
import logging
import re
from datetime import datetime as dt

from telegram import ForceReply, Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, \
    ReplyKeyboardRemove, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, \
    CallbackQueryHandler

from db_interact import reg_user, add_birth, get_births_by_chat_id, check_is_user_own_row, delete_birth_row

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

MENU, INPUT_DATE, INPUT_CELEBRANT, CONFIRMATION, DELETE_BIRTH = range(5)

reply_keyboard = [
    ["Новая запись"],
    ["Посмотреть все записи", "Удалить запись"]
]

reply_keyboard_inline = [
    [InlineKeyboardButton(text="Назад", callback_data="1"), InlineKeyboardButton(text="Отмена", callback_data="2")]
]

markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
markup_inline = InlineKeyboardMarkup(reply_keyboard_inline)


cancel_inline = [
        [InlineKeyboardButton(text="Отмена", callback_data="cancel")]
    ]
cancel_markup = InlineKeyboardMarkup(cancel_inline)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reg_user(update.message.chat.id)
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
        await update.message.reply_text("Неверный формат ID для удаления. Укажите целочисленный ID", reply_markup=cancel_markup)
        return DELETE_BIRTH

    if check_is_user_own_row(chat_id, row_id):
        delete_birth_row(row_id)
        await update.message.reply_text(f"Запись с ID {row_id} успешно удалена",
                                        reply_markup=markup)
    else:
        await update.message.reply_text(f"Запись с ID {row_id} не найдена или вы не являетесь её владельцем",
                                        reply_markup=cancel_markup)
        return DELETE_BIRTH

    return MENU

def is_int(val):
    try:
        num = int(val)
        return True
    except (TypeError, ValueError):
        return False


async def get_all_rows(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tuples = get_births_by_chat_id(update.message.chat.id)
    if len(tuples) == 0:
        await update.message.reply_text("Список пуст")
        return MENU

    res = ''
    for x in tuples:
        res += f"Дата: {x[3]}.{x[4]}" + (f'.{x[5]}' if x[5] != 'NULL' and '' else '') + f". Имя: {x[1]}." + f' Id: {x[0]} ' + '\n'

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
        await update.message.reply_text("Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ или ДД.ММ.ГГГГ.",
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
    add_birth(chat_id, context.user_data["celebrant"], res)

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

def is_valid_date(date_str):
    # Проверяем, что строка соответствует формату дд.мм.гггг
    date_pattern = r"^\d{2}\.\d{2}(\.\d{4})?$"
    if not re.match(date_pattern, date_str):
        return False

    # Преобразуем строку в объект datetime и проверяем на валидность
    try:
        # if len(date_str):
        #     date_str = date_str + ".0001"
        pattern = "%d.%m.%Y" if len(date_str) == 10 else "%d.%m"
        dt.strptime(date_str, pattern)
        return True
    except ValueError:
        return False

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
   await update.message.reply_text("Нераспознанная команда, используйте /start для начала работы")

def main() -> None:
    application = Application.builder().token("7326645467:AAEyzGJh_Et1ceYuxZezhsdQKxlL5zD3TaI").build()

    # on different commands - answer in Telegram

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("showpanel", show_panel_command)],
        states={
            MENU: [
                MessageHandler(filters.Regex("^Новая запись$"), add_birth_command),
                MessageHandler(filters.Regex("^Посмотреть все записи$"), get_all_rows),
                MessageHandler(filters.Regex("^Удалить запись$"), delete_birth)
            ],
            INPUT_DATE: [MessageHandler(filters.TEXT, input_date)],
            INPUT_CELEBRANT: [MessageHandler(filters.TEXT, input_celebrant)],
            CONFIRMATION: [
                CallbackQueryHandler(confirm, pattern="^yes$"),
                CallbackQueryHandler(deny, pattern="^no$")
            ],
            DELETE_BIRTH: [
                MessageHandler(filters.TEXT, execute_delete)
            ]
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
    )

    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()