from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import os

app = FastAPI()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 AI Engineering Assistant\n\n"
        "✅ Bot is online on Vercel.\n"
        "Send me a question."
    )


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Telegram webhook is working.\n\n"
        f"Your message:\n{update.message.text}"
    )


telegram_app = (
    Application.builder()
    .token(TOKEN)
    .build()
)

telegram_app.add_handler(
    CommandHandler("start", start)
)

telegram_app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        text_message
    )
)


@app.get("/")
async def health():
    return {"ok": True, "service": "AI Engineering Assistant"}


@app.post("/api")
async def telegram_webhook(request: Request):

    data = await request.json()

    update = Update.de_json(
        data,
        telegram_app.bot
    )

    await telegram_app.initialize()
    await telegram_app.process_update(update)
    await telegram_app.shutdown()

    return {"ok": True}