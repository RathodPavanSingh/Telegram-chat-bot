from telegram.ext import CommandHandler, MessageHandler, filters, Application

from bot import ai_chat, help_command, image_question, start
from config import TELEGRAM_BOT_TOKEN

def build_application():

    bot_app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    bot_app.add_handler(
        CommandHandler("start", start)
    )

    bot_app.add_handler(
        CommandHandler("help", help_command)
    )

    bot_app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            ai_chat
        )
    )

    bot_app.add_handler(
        MessageHandler(
            filters.PHOTO,
            image_question
        )
    )

    return bot_app