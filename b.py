import asyncio
import logging
import sqlite3
import os
from datetime import datetime
from dataclasses import dataclass
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# Konfiguratsiya
BOT_TOKEN = "7873772519:AAE78dcNv5oxz40jiMJQNxIdoqM4PBpuizY"
ADMIN_IDS = [6752780496]

# PythonAnywhere uchun yo'llar
BASE_DIR = '/home/SobirjonDev06'
os.makedirs(os.path.join(BASE_DIR, 'photos'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'files'), exist_ok=True)
DB_PATH = os.path.join(BASE_DIR, 'car_bot.db')

# Webhook sozlamalari
WEBHOOK_HOST = "https://SobirjonDev06.pythonanywhere.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBAPP_HOST = "0.0.0.0"  # PythonAnywhere uchun
WEBAPP_PORT = 8000       # PythonAnywhere uchun

# Bot va dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Ma'lumotlar bazasini ishga tushirish
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL,
        photo_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

# Botni ishga tushirish funksiyalari
async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)
    logging.info("Bot webhook orqali ishga tushdi!")

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    logging.info("Bot to'xtatildi!")

# Asosiy commandalar
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Assalomu alaykum! Bu sizning avtosalon botingiz.")

# Web application yaratish
def create_app():
    app = web.Application()
    app.router.add_get("/", lambda request: web.Response(text="Bot ishlayapti!"))
    
    # Webhook handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    # Application setup
    setup_application(app, dp, bot=bot)
    
    return app

if __name__ == "__main__":
    # Ma'lumotlar bazasini ishga tushirish
    init_db()
    
    # Logging sozlamalari
    logging.basicConfig(level=logging.INFO)
    
    # Web application yaratish
    app = create_app()
    
    # Ishga tushirish funksiyalari
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    # Serverni ishga tushirish
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)