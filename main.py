import logging
from config import TOKEN

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, \
    CallbackQueryHandler

from handlers import start, show_panel_command, add_birth_command, get_all_rows, delete_birth, \
    get_list_of_the_next_30_days, input_date, input_celebrant, confirm, deny, execute_delete, cancel, \
    MENU, INPUT_DATE, INPUT_CELEBRANT, CONFIRMATION, DELETE_BIRTH

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("showpanel", show_panel_command)],
        states={
            MENU: [
                MessageHandler(filters.Regex("^Новая запись$"), add_birth_command),
                MessageHandler(filters.Regex("^Посмотреть все записи$"), get_all_rows),
                MessageHandler(filters.Regex("^Удалить запись$"), delete_birth),
                MessageHandler(filters.Regex("^Список на 30 дней$"), get_list_of_the_next_30_days)
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
