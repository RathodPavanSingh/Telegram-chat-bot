import asyncio
from fastapi import FastAPI, Request
from telegram import Update

from bot import build_application

app = FastAPI()

telegram_app = None


@app.on_event("startup")
async def startup_event():
    global telegram_app

    telegram_app = build_application()

    await telegram_app.initialize()


@app.post("/")
async def telegram_webhook(request: Request):

    global telegram_app

    data = await request.json()

    update = Update.de_json(
        data,
        telegram_app.bot
    )

    await telegram_app.process_update(update)

    return {"ok": True}