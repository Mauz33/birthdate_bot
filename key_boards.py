from telegram import InlineKeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup

reply_keyboard = [
    ["Новая запись", "Список на 30 дней"],
    ["Посмотреть все записи", "Удалить запись"]
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)


reply_keyboard_inline = [
    [InlineKeyboardButton(text="Назад", callback_data="1"), InlineKeyboardButton(text="Отмена", callback_data="2")]
]
markup_inline = InlineKeyboardMarkup(reply_keyboard_inline)


cancel_inline = [
        [InlineKeyboardButton(text="Отмена", callback_data="cancel")]
    ]
cancel_markup = InlineKeyboardMarkup(cancel_inline)

