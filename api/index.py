import os

from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from google import genai

app = FastAPI()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)

if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")

client = genai.Client(
    api_key=GEMINI_API_KEY
)

telegram_app = (
    Application.builder()
    .token(TOKEN)
    .build()
)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🤖 AI Engineering Assistant\n\n"
        "✅ Vercel webhook is working."
    )


async def text_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    question = (
        update.message.text or ""
    ).strip()

    if not question:
        return

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=(
                "You are a professional AI Engineering Assistant.\n"
                "Answer clearly and accurately.\n"
                "Use Unicode symbols instead of raw LaTeX.\n\n"
                f"Question:\n{question}"
            )
        )

        answer = (
            response.text.strip()
            if response.text
            else "❌ No answer generated."
        )

        await update.message.reply_text(
            answer
        )

    except Exception as e:

        print("❌ AI ERROR:", repr(e))

        await update.message.reply_text(
            "⚠️ AI service is currently unavailable."
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
    return {
        "ok": True,
        "service": "AI Engineering Assistant"
    }


@app.post("/")
async def telegram_webhook(
    request: Request
):

    try:
        data = await request.json()

        update = Update.de_json(
            data,
            telegram_app.bot
        )

        await telegram_app.initialize()

        await telegram_app.process_update(
            update
        )

        return {"ok": True}

    except Exception as e:

        print(
            "❌ WEBHOOK ERROR:",
            repr(e)
        )

        return {
            "ok": False,
            "error": str(e)
        }