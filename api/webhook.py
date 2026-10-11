"""
Точка входа для Vercel: Telegram шлёт сюда каждое обновление (webhook).
Каждый вызов - отдельный короткий запуск, поэтому всё состояние партии
хранится в Supabase, а не в памяти.
"""
import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aiogram import Bot, Dispatcher
from aiogram.types import Update

from bot.handlers import lobby

dp = Dispatcher()
dp.include_router(lobby.router)


async def process_update(data: dict):
    bot = Bot(token=os.environ["BOT_TOKEN"])
    try:
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
    finally:
        await bot.session.close()


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        secret = os.environ.get("WEBHOOK_SECRET")
        if secret and self.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
            self.send_response(403)
            self.end_headers()
            return

        length = int(self.headers.get("content-length", 0))
        body = self.rfile.read(length)
        try:
            asyncio.run(process_update(json.loads(body)))
        except Exception as e:
            print("update error:", repr(e))

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Secret Hitler bot is alive")
