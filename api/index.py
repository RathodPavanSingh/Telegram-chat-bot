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

bot_app = (
    Application.builder()
    .token(TOKEN)
    .build()
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 AI Engineering Assistant\n\n"
        "✅ Vercel webhook is working."
    )


async def text_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    text = (update.message.text or "").strip()

    await update.message.reply_text(
        "✅ Message received!\n\n"
        f"You said:\n{text}"
    )


bot_app.add_handler(
    CommandHandler("start", start)
)

bot_app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        text_message
    )
)


@app.get("/")
@app.get("/api")
async def health():
    return {
        "ok": True,
        "service": "AI Engineering Assistant"
    }


@app.post("/")
@app.post("/api")
async def webhook(request: Request):

    try:
        data = await request.json()

        update = Update.de_json(
            data,
            bot_app.bot
        )

        await bot_app.initialize()
        await bot_app.process_update(update)

        return {"ok": True}

    except Exception as e:
        print("WEBHOOK ERROR:", repr(e))
        return {
            "ok": False,
            "error": str(e)
        }