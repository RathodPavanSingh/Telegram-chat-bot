import os

from fastapi import FastAPI, Request
from telegram import Update
from database import SessionLocal, User, Conversation
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

def get_or_create_user(telegram_user):
    db = SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(
                User.telegram_user_id == telegram_user.id
            )
            .first()
        )

        if not user:
            user = User(
                telegram_user_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
                language="en"
            )
            db.add(user)
        else:
            user.username = telegram_user.username
            user.first_name = telegram_user.first_name
            user.last_name = telegram_user.last_name

        db.commit()
        db.refresh(user)

        return user

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def save_message(telegram_user_id, role, message):
    db = SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(
                User.telegram_user_id == telegram_user_id
            )
            .first()
        )

        if not user:
            return

        db.add(
            Conversation(
                user_id=user.id,
                role=role,
                message=message
            )
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def get_history(telegram_user_id, limit=10):
    db = SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(
                User.telegram_user_id == telegram_user_id
            )
            .first()
        )

        if not user:
            return []

        rows = (
            db.query(Conversation)
            .filter(
                Conversation.user_id == user.id
            )
            .order_by(
                Conversation.created_at.desc()
            )
            .limit(limit)
            .all()
        )

        rows.reverse()

        return rows

    finally:
        db.close()

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🤖 AI Engineering Assistant\n\n"
        "Ask me anything about:\n"
        "⚡ Engineering\n"
        "💻 Coding\n"
        "🧮 Mathematics\n"
        "📚 Education"
    )


async def text_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    question = update.message.text.strip()

    if not question:
        return

    telegram_user = update.effective_user

    try:

        user = get_or_create_user(
            telegram_user
        )

        history = get_history(
            telegram_user.id,
            limit=10
        )

        conversation = ""

        for item in history:
            conversation += (
                f"{item.role}: {item.message}\n"
            )

        prompt = (
            "You are a professional AI Engineering Assistant.\n"
            "Answer clearly and accurately.\n"
            "For mathematics and engineering, show steps and units.\n"
            "For coding, provide correct runnable code.\n"
            "Use readable Unicode math symbols instead of raw LaTeX.\n\n"
            "Previous conversation:\n"
            f"{conversation}\n"
            "Latest question:\n"
            f"{question}"
        )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        answer = (
            response.text.strip()
            if response.text
            else "❌ No answer was generated."
        )

        save_message(
            telegram_user.id,
            "user",
            question
        )

        save_message(
            telegram_user.id,
            "assistant",
            answer
        )

        await update.message.reply_text(
            answer
        )

    except Exception as e:

        print(
            "❌ AI/DATABASE ERROR:",
            repr(e)
        )

        await update.message.reply_text(
            "⚠️ I couldn't process your request."
        )
async def clear_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(
                User.telegram_user_id == user_id
            )
            .first()
        )

        if user:
            db.query(Conversation).filter(
                Conversation.user_id == user.id
            ).delete()

            db.commit()

        await update.message.reply_text(
            "🧹 Conversation history cleared."
        )

    except Exception as e:

        db.rollback()

        print(
            "❌ CLEAR ERROR:",
            repr(e)
        )

        await update.message.reply_text(
            "❌ Could not clear conversation history."
        )

    finally:

        db.close()        

telegram_app.add_handler(
    CommandHandler("start", start)
)

telegram_app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        text_message
    )
)

telegram_app.add_handler(
    CommandHandler("clear", clear_command)
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

    data = await request.json()

    update = Update.de_json(
        data,
        telegram_app.bot
    )

    await telegram_app.initialize()

    await telegram_app.process_update(
        update
    )

    return {
        "ok": True
    }