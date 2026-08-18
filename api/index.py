from fastapi import FastAPI, Request
from telegram import Update
from google import genai
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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)

client = genai.Client(
    api_key=GEMINI_API_KEY
)
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

    question = (update.message.text or "").strip()

    if not question:
        return

    try:
        print(f"📩 User: {question}")
        print("🤖 Sending request to Gemini...")

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=(
                "You are a professional AI Engineering Assistant.\n\n"
                "Answer the user's question clearly and accurately.\n"
                "For mathematics and engineering, show steps and units.\n"
                "For programming, provide correct runnable code.\n"
                "Use Unicode symbols instead of raw LaTeX.\n\n"
                f"Question:\n{question}"
            )
        )

        answer = (
            response.text.strip()
            if response.text
            else "❌ No answer generated."
        )

        await update.message.reply_text(answer)

    except Exception as e:

        print("================================")
        print("❌ AI ERROR")
        print(repr(e))
        print("================================")

        await update.message.reply_text(
            "⚠️ AI service is currently unavailable."
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