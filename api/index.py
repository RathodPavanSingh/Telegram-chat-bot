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
import base64
from io import BytesIO

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
#====
#image_message
async def image_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:
        if not update.message or not update.message.photo:
            return

        await update.message.reply_text(
            "📷 Image received.\n"
            "🔍 Analyzing the question..."
        )

        # Highest-resolution photo
        photo = update.message.photo[-1]

        # Download image from Telegram
        telegram_file = await context.bot.get_file(
            photo.file_id
        )

        image_bytes = await telegram_file.download_as_bytearray()

        # Convert bytes to base64
        image_b64 = base64.b64encode(
            bytes(image_bytes)
        ).decode("utf-8")

        # Gemini multimodal request
        interaction = client.interactions.create(
            model=GEMINI_MODEL,
            input=[
                {
                    "type": "text",
                    "text": (
                        "Analyze the uploaded image.\n\n"
                        "If it contains a question, solve it.\n"
                        "For mathematics, show steps.\n"
                        "For engineering, include formulas and units.\n"
                        "For programming, provide correct code.\n"
                        "Use readable Unicode mathematical symbols "
                        "instead of raw LaTeX."
                    )
                },
                {
                    "type": "image",
                    "data": image_b64,
                    "mime_type": "image/jpeg"
                }
            ]
        )

        answer = interaction.output_text

        if not answer:
            answer = "❌ I couldn't understand the image."

        await update.message.reply_text(
            answer
        )

    except Exception as e:

        print("================================")
        print("❌ IMAGE ERROR")
        print(repr(e))
        print("================================")

        await update.message.reply_text(
            "❌ I couldn't process the image.\n\n"
            "Please upload a clearer image."
        )
# ====        
async def telegram_error_handler(update, context):
    error = context.error

    print("================================")
    print("❌ TELEGRAM/APP ERROR")
    print(repr(error))
    print("================================")

    # Do not hide database / application errors as network errors.
    message = "❌ An error occurred while processing your request."

    if "UndefinedColumn" in str(error):
        message = (
            "❌ Database schema is outdated.\n\n"
            "Please update the PostgreSQL tables."
        )

    elif "does not exist" in str(error):
        message = (
            "❌ Database/table configuration problem.\n\n"
            "Please check DATABASE_URL and PostgreSQL tables."
        )

    elif "Conflict" in str(error):
        message = (
            "⚠️ Another bot instance is running.\n\n"
            "Stop the other bot process and try again."
        )

    elif "TimedOut" in str(error) or "NetworkError" in str(error):
        message = (
            "⚠️ Telegram network connection timed out.\n"
            "Please try again."
        )

    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                message
            )
    except Exception as send_error:
        print(
            "❌ ERROR SENDING ERROR MESSAGE:",
            repr(send_error)
        )

bot_app.add_handler(
    CommandHandler("start", start)
)
bot_app.add_handler(
    MessageHandler(
        filters.PHOTO,
        image_question
    )
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