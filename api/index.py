import os

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

from database import (
    SessionLocal,
    User,
    Conversation,
)

app = FastAPI()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
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


def get_or_create_user(tg_user):
    db = SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(
                User.telegram_user_id == tg_user.id
            )
            .first()
        )

        if user is None:
            user = User(
                telegram_user_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                language="en",
            )
            db.add(user)
        else:
            user.username = tg_user.username
            user.first_name = tg_user.first_name
            user.last_name = tg_user.last_name
            user.last_seen = __import__(
                "datetime"
            ).datetime.now(
                __import__("datetime").timezone.utc
            )

        db.commit()
        return user

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def save_message(user_id, role, message):
    db = SessionLocal()

    try:
        db.add(
            Conversation(
                telegram_user_id=user_id,
                role=role,
                message=message,
            )
        )
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_or_create_user(update.effective_user)

    await update.message.reply_text(
        "🤖 AI Engineering Assistant\n\n"
        "✅ Online\n\n"
        "Ask me anything about engineering, coding, "
        "mathematics, physics, education, or general topics."
    )


async def text_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    question = (update.message.text or "").strip()

    if not question:
        return

    user_id = update.effective_user.id

    try:
        get_or_create_user(
            update.effective_user
        )

        print(
            f"📩 User {user_id}: {question}"
        )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=(
                "You are a professional AI Engineering Assistant.\n\n"
                "Answer clearly and accurately.\n"
                "For mathematics and engineering, show steps "
                "and units.\n"
                "For programming, provide runnable code.\n"
                "Use readable Unicode symbols instead of raw LaTeX.\n\n"
                f"Question:\n{question}"
            ),
        )

        answer = (
            response.text.strip()
            if response.text
            else "❌ No answer generated."
        )

        save_message(
            user_id,
            "user",
            question,
        )

        save_message(
            user_id,
            "assistant",
            answer,
        )

        await update.message.reply_text(
            answer
        )

    except Exception as e:
        print(
            "❌ AI ERROR:",
            repr(e)
        )

        await update.message.reply_text(
            "⚠️ AI service is currently unavailable."
        )


telegram_app.add_handler(
    CommandHandler("start", start)
)

telegram_app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        text_message,
    )
)


@app.get("/api")
async def health():
    return {
        "ok": True,
        "service": "AI Engineering Assistant",
    }


@app.post("/api")
async def telegram_webhook(
    request: Request,
):
    data = await request.json()

    update = Update.de_json(
        data,
        telegram_app.bot,
    )

    await telegram_app.initialize()

    try:
        await telegram_app.process_update(
            update
        )
    finally:
        await telegram_app.shutdown()

    return {"ok": True}