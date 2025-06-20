import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
import sqlite3
import os
from dataclasses import dataclass
from enum import Enum

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputFile, FSInputFile, Update
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import re


# Configuration
BOT_TOKEN = ("7873772519:AAE78dcNv5oxz40jiMJQNxIdoqM4PBpuizY")
ADMIN_IDS = [6752780496]  # Add admin user IDs here

WEBHOOK_HOST = "https://SobirjonDev06.pythonanywhere.com"  # username.pythonanywhere.com
WEBHOOK_PATH = "/webhook"  # soddaroq yo'l
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# PythonAnywhere paths
BASE_DIR = '/home/SobirjonDev06'  # o'z username'ingizni yozing
PHOTOS_DIR = os.path.join(BASE_DIR, 'photos')
FILES_DIR = os.path.join(BASE_DIR, 'files')
DB_PATH = os.path.join(BASE_DIR, 'car_bot.db')

# Web app configuration
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = 8000

# Database setup
def init_db():
    # PythonAnywhere uchun to'liq path ishlatish
    db_path = os.path.join(os.path.expanduser('~'), 'car_bot.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        language TEXT DEFAULT 'uz',
        is_admin BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Cars table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL,
        car_type TEXT CHECK(car_type IN ('cash', 'credit')),
        photo_path TEXT,
        credit_months INTEGER,
        credit_percent REAL,
        initial_payment REAL,
        credit_note TEXT,
        additional_note TEXT,
        file_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT TRUE
    )
    ''')
    
    # Applications table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        car_id INTEGER,
        user_comment TEXT,
        phone_number TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (car_id) REFERENCES cars (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Database helper function
def get_db_connection():
    db_path = os.path.join(os.path.expanduser('~'), 'car_bot.db')
    return sqlite3.connect(db_path)

# States
class AddCarStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_type = State()
    waiting_for_credit_months = State()
    waiting_for_credit_percent = State()
    waiting_for_initial_payment = State()
    waiting_for_credit_note = State()
    waiting_for_additional_note = State()
    waiting_for_file = State()

class ApplicationStates(StatesGroup):
    waiting_for_comment = State()
    waiting_for_phone = State()

class SearchStates(StatesGroup):
    waiting_for_search_query = State()

class EditCarStates(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_description = State()
    waiting_for_new_price = State()
    waiting_for_new_photo = State()
    waiting_for_new_credit_months = State()
    waiting_for_new_credit_percent = State()
    waiting_for_new_initial_payment = State()
    waiting_for_new_credit_note = State()

# Data classes
@dataclass
class Car:
    id: int
    name: str
    description: str
    price: float
    car_type: str
    photo_path: str
    credit_months: int = None
    credit_percent: float = None
    initial_payment: float = None
    credit_note: str = None
    additional_note: str = None
    file_path: str = None

@dataclass
class Application:
    id: int
    user_id: int
    car_id: int
    user_comment: str
    phone_number: str
    status: str
    created_at: str
    car_name: str = None
    user_name: str = None

# Language texts
TEXTS = {
    'uz': {
        'welcome': "🚗 Avtosalon botiga xush kelibsiz!\n\nTilni tanlang:",
        'main_menu': "🏠 Asosiy menyu",
        'view_cars': "🚗 Mashinalarni ko'rish",
        'search_cars': "🔍 Mashina qidirish", 
        'my_applications': "📋 Arizalarim",
        'admin_panel': "👨‍💼 Admin panel",
        'cash': "💰 Naqd",
        'credit': "💳 Kredit",
        'back': "🔙 Orqaga",
        'submit_application': "✅ Ariza yuborish",
        'enter_comment': "✍️ Izoh kiriting:",
        'share_contact': "📞 Telefon raqamingizni ulashing:",
        'application_sent': "✅ Arizangiz yuborildi! Tez orada siz bilan bog'lanamiz.",
        'no_cars_found': "❌ Mashinalar topilmadi",
        'enter_search_query': "🔍 Mashina nomini kiriting:",
        'no_applications': "📋 Sizda hozircha arizalar yo'q",
        'add_car': "➕ Mashina qo'shish",
        'delete_car': "❌ Mashina o'chirish", 
        'view_applications': "📋 Arizalarni ko'rish",
        'pending': "🟡 Kutilmoqda",
        'approved': "✅ Tasdiqlandi",
        'rejected': "❌ Rad etildi",
        'edit': "✏️ Tahrirlash",
        'all_car': "📋 Barcha mashinalar"
    },
    'ru': {
        'welcome': "🚗 Добро пожаловать в бот автосалона!\n\nВыберите язык:",
        'main_menu': "🏠 Главное меню",
        'view_cars': "🚗 Посмотреть машины",
        'search_cars': "🔍 Поиск машин",
        'my_applications': "📋 Мои заявки", 
        'admin_panel': "👨‍💼 Админ панель",
        'cash': "💰 Наличные",
        'credit': "💳 Кредит",
        'back': "🔙 Назад",
        'submit_application': "✅ Подать заявку",
        'enter_comment': "✍️ Введите комментарий:",
        'share_contact': "📞 Поделитесь своим номером телефона:",
        'application_sent': "✅ Ваша заявка отправлена! Скоро с вами свяжемся.",
        'no_cars_found': "❌ Машины не найдены",
        'enter_search_query': "🔍 Введите название машины:",
        'no_applications': "📋 У вас пока нет заявок",
        'add_car': "➕ Добавить машину",
        'delete_car': "❌ Удалить машину",
        'view_applications': "📋 Посмотреть заявки", 
        'pending': "🟡 Ожидает",
        'approved': "✅ Одобрено",
        'rejected': "❌ Отклонено",
        'edit': "✏️ Редактировать",
        'all_car': "📋 Все машины"
    }
}

# Database functions
def get_user_language(user_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 'uz'

def save_user(user_id: int, username: str, full_name: str, language: str = 'uz'):
    conn = get_db_connection()
    cursor = conn.cursor()
    is_admin = user_id in ADMIN_IDS
    cursor.execute('''
    INSERT OR REPLACE INTO users (user_id, username, full_name, language, is_admin)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, full_name, language, is_admin))
    conn.commit()
    conn.close()

def get_cars(car_type: str = None) -> List[Car]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if car_type:
        cursor.execute("SELECT * FROM cars WHERE car_type = ? AND is_active = TRUE", (car_type,))
    else:
        cursor.execute("SELECT * FROM cars WHERE is_active = TRUE")
    
    rows = cursor.fetchall()
    conn.close()
    
    cars = []
    for row in rows:
        cars.append(Car(
            id=row[0], name=row[1], description=row[2], price=row[3],
            car_type=row[4], photo_path=row[5], credit_months=row[6],
            credit_percent=row[7], initial_payment=row[8], credit_note=row[9],
            additional_note=row[10], file_path=row[11]
        ))
    return cars

def search_cars(query: str) -> List[Car]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM cars WHERE name LIKE ? AND is_active = TRUE", 
        (f'%{query}%',)
    )
    rows = cursor.fetchall()
    conn.close()
    
    cars = []
    for row in rows:
        cars.append(Car(
            id=row[0], name=row[1], description=row[2], price=row[3],
            car_type=row[4], photo_path=row[5], credit_months=row[6], 
            credit_percent=row[7], initial_payment=row[8], credit_note=row[9],
            additional_note=row[10], file_path=row[11]
        ))
    return cars

def save_application(user_id: int, car_id: int, comment: str, phone: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO applications (user_id, car_id, user_comment, phone_number)
    VALUES (?, ?, ?, ?)
    ''', (user_id, car_id, comment, phone))
    conn.commit()
    conn.close()

def get_user_applications(user_id: int) -> List[Application]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT a.*, c.name as car_name 
    FROM applications a
    JOIN cars c ON a.car_id = c.id
    WHERE a.user_id = ?
    ORDER BY a.created_at DESC
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    applications = []
    for row in rows:
        app = Application(
            id=row[0], user_id=row[1], car_id=row[2], 
            user_comment=row[3], phone_number=row[4],
            status=row[5], created_at=row[6], car_name=row[7]
        )
        applications.append(app)
    return applications

def save_car(car_data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO cars (name, description, price, car_type, photo_path, 
                     credit_months, credit_percent, initial_payment, 
                     credit_note, additional_note, file_path)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        car_data['name'], car_data['description'], car_data['price'],
        car_data['car_type'], car_data['photo_path'], car_data.get('credit_months'),
        car_data.get('credit_percent'), car_data.get('initial_payment'),
        car_data.get('credit_note'), car_data['additional_note'], car_data.get('file_path')
    ))
    conn.commit()
    conn.close()

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Helper functions
def get_text(user_id: int, key: str) -> str:
    lang = get_user_language(user_id)
    return TEXTS[lang].get(key, key)

def get_main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    lang = get_user_language(user_id)
    buttons = [
        [KeyboardButton(text=TEXTS[lang]['view_cars'])],
        [KeyboardButton(text=TEXTS[lang]['all_car'])],
        [KeyboardButton(text=TEXTS[lang]['search_cars'])],
        [KeyboardButton(text=TEXTS[lang]['my_applications'])]
    ]
    
    if user_id in ADMIN_IDS:
        buttons.append([KeyboardButton(text=TEXTS[lang]['admin_panel'])])
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_admin_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    lang = get_user_language(user_id)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=TEXTS[lang]['add_car'])],
            [KeyboardButton(text=TEXTS[lang]['delete_car'])],
            [KeyboardButton(text=TEXTS[lang]['all_car'])],
            [KeyboardButton(text=TEXTS[lang]['edit'])],
            [KeyboardButton(text=TEXTS[lang]['view_applications'])],
            [KeyboardButton(text=TEXTS[lang]['back'])]
        ],
        resize_keyboard=True
    )

def format_car_message(car: Car, user_id: int) -> str:
    lang = get_user_language(user_id)
    
    message = f"🚗 **{car.name}**\n\n"
    message += f"📝 {car.description}\n\n"
    message += f"💰 Narx: {car.price:,.0f} so'm\n"
    message += f"🏷️ Turi: {TEXTS[lang][car.car_type]}\n\n"
    
    if car.car_type == 'credit' and car.credit_months:
        message += f"💳 **Kredit shartlari:**\n"
        message += f"📅 Muddat: {car.credit_months} oy\n"
        if car.credit_percent:
            message += f"📊 Foiz: {car.credit_percent}%\n"
        if car.initial_payment:
            message += f"💵 Boshlang'ich to'lov: {car.initial_payment:,.0f} so'm\n"
        if car.credit_note:
            message += f"📋 Kredit izohi: {car.credit_note}\n"
        message += "\n"
    
    if car.additional_note:
        message += f"💬 Qo'shimcha ma'lumot: {car.additional_note}\n"
    
    return message

# Constants for pagination
CARS_PER_PAGE = 10

# Handlers
@dp.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    
    # Language selection keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")]
    ])
    
    await message.answer(
        "🚗 Avtosalon botiga xush kelibsiz!\n\nTilni tanlang:\n\n"
        "🚗 Добро пожаловать в бот автосалона!\n\nВыберите язык:",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("lang_"))
async def language_selection(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    user = callback.from_user
    
    save_user(user.id, user.username, user.full_name, lang)
    
    await callback.message.edit_text(
        get_text(user.id, 'welcome'),
        reply_markup=None
    )
    
    await callback.message.answer(
        get_text(user.id, 'main_menu'),
        reply_markup=get_main_keyboard(user.id)
    )

@dp.message(F.text.in_([
    "🚗 Mashinalarni ko'rish", "🚗 Посмотреть машины"
]))
async def view_cars_handler(message: Message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=TEXTS[lang]['cash'], callback_data="cars_cash")],
        [InlineKeyboardButton(text=TEXTS[lang]['credit'], callback_data="cars_credit")]
    ])
    
    await message.answer(
        "Qaysi turdagi mashinalarni ko'rmoqchisiz?",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("cars_"))
async def show_cars(callback: CallbackQuery):
    car_type = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    cars = get_cars(car_type)
    
    if not cars:
        await callback.message.edit_text(get_text(user_id, 'no_cars_found'))
        return
    
    await callback.message.delete()
    
    for car in cars:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=get_text(user_id, 'submit_application'),
                callback_data=f"apply_{car.id}"
            )]
        ])
        
        message_text = format_car_message(car, user_id)
        
        # PythonAnywhere uchun photos papkasining to'liq yo'li
        photos_dir = os.path.join(os.path.expanduser('~'), 'photos')
        if car.photo_path:
            full_photo_path = os.path.join(photos_dir, os.path.basename(car.photo_path))
            if os.path.exists(full_photo_path):
                await callback.message.answer_photo(
                    photo=FSInputFile(full_photo_path),
                    caption=message_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            else:
                await callback.message.answer(
                    message_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
        else:
            await callback.message.answer(
                message_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

@dp.callback_query(F.data.startswith("apply_"))
async def start_application(callback: CallbackQuery, state: FSMContext):
    car_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    await state.update_data(car_id=car_id)
    await state.set_state(ApplicationStates.waiting_for_comment)
    
    await callback.message.answer(get_text(user_id, 'enter_comment'))

@dp.message(StateFilter(ApplicationStates.waiting_for_comment))
async def process_comment(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    await state.update_data(comment=message.text)
    await state.set_state(ApplicationStates.waiting_for_phone)
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Telefon raqamni ulashish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        get_text(user_id, 'share_contact'),
        reply_markup=keyboard
    )

@dp.message(StateFilter(ApplicationStates.waiting_for_phone), F.contact)
async def process_phone(message: Message, state: FSMContext):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    
    data = await state.get_data()
    car_id = data['car_id']
    comment = data['comment']
    
    save_application(user_id, car_id, comment, phone)
    await state.clear()
    
    await message.answer(
        get_text(user_id, 'application_sent'),
        reply_markup=get_main_keyboard(user_id)
    )

@dp.message(F.text.in_(["🔍 Mashina qidirish", "🔍 Поиск машин"]))
async def search_cars_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.set_state(SearchStates.waiting_for_search_query)
    
    await message.answer(get_text(user_id, 'enter_search_query'))

@dp.message(StateFilter(SearchStates.waiting_for_search_query))
async def process_search(message: Message, state: FSMContext):
    user_id = message.from_user.id
    query = message.text
    
    cars = search_cars(query)
    await state.clear()
    
    if not cars:
        await message.answer(
            get_text(user_id, 'no_cars_found'),
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    for car in cars:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=get_text(user_id, 'submit_application'),
                callback_data=f"apply_{car.id}"
            )]
        ])
        
        message_text = format_car_message(car, user_id)
        
        photos_dir = os.path.join(os.path.expanduser('~'), 'photos')
        if car.photo_path:
            full_photo_path = os.path.join(photos_dir, os.path.basename(car.photo_path))
            if os.path.exists(full_photo_path):
                await message.answer_photo(
                    photo=FSInputFile(full_photo_path),
                    caption=message_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            else:
                await message.answer(
                    message_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
        else:
            await message.answer(
                message_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

@dp.message(F.text.in_(["📋 Arizalarim", "📋 Мои заявки"]))
async def my_applications_handler(message: Message):
    user_id = message.from_user.id
    applications = get_user_applications(user_id)
    
    if not applications:
        await message.answer(get_text(user_id, 'no_applications'))
        return
    
    for app in applications:
        status_text = get_text(user_id, app.status)
        message_text = f"🚗 **{app.car_name}**\n"
        message_text += f"📝 Izoh: {app.user_comment}\n"
        message_text += f"📞 Telefon: {app.phone_number}\n"
        message_text += f"📅 Sana: {app.created_at}\n"
        message_text += f"📊 Holat: {status_text}"
        
        await message.answer(message_text, parse_mode="Markdown")

# All cars handler
@dp.message(F.text.in_(["📋 Barcha mashinalar", "📋 Все машины"]))
async def view_all_cars_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await show_cars_page(message, user_id, page=1)

async def show_cars_page(message: Message, user_id: int, page: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM cars WHERE is_active = TRUE")
    total_cars = cursor.fetchone()[0]
    
    offset = (page - 1) * CARS_PER_PAGE
    cursor.execute("""
        SELECT * FROM cars 
        WHERE is_active = TRUE 
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """, (CARS_PER_PAGE, offset))
    
    cars = cursor.fetchall()
    conn.close()
    
    if not cars:
        await message.answer("❌ Mashinalar topilmadi")
        return
    
    for car_data in cars:
        car = Car(
            id=car_data[0], name=car_data[1], description=car_data[2],
            price=car_data[3], car_type=car_data[4], photo_path=car_data[5],
            credit_months=car_data[6], credit_percent=car_data[7],
            initial_payment=car_data[8], credit_note=car_data[9],
            additional_note=car_data[10], file_path=car_data[11]
        )
        
        message_text = format_car_message(car, user_id)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=get_text(user_id, 'submit_application'),
                callback_data=f"apply_{car.id}"
            )]
        ])
        
        photos_dir = os.path.join(os.path.expanduser('~'), 'photos')
        if car.photo_path:
            full_photo_path = os.path.join(photos_dir, os.path.basename(car.photo_path))
            if os.path.exists(full_photo_path):
                await message.answer_photo(
                    photo=FSInputFile(full_photo_path),
                    caption=message_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            else:
                await message.answer(
                    message_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
        else:
            await message.answer(
                message_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    
    total_pages = (total_cars + CARS_PER_PAGE - 1) // CARS_PER_PAGE
    
    if total_pages > 1:
        navigation_buttons = []
        
        if page > 1:
            navigation_buttons.append(
                InlineKeyboardButton(
                    text="◀️ Oldingi",
                    callback_data=f"cars_page_{page-1}"
                )
            )
        
        if page < total_pages:
            navigation_buttons.append(
                InlineKeyboardButton(
                    text="Keyingi ▶️",
                    callback_data=f"cars_page_{page+1}"
                )
            )
        
        nav_markup = InlineKeyboardMarkup(inline_keyboard=[navigation_buttons])
        await message.answer(
            f"📋 Sahifa {page}/{total_pages}",
            reply_markup=nav_markup
        )

@dp.callback_query(F.data.startswith("cars_page_"))
async def process_cars_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    await callback.message.delete()
    await show_cars_page(callback.message, callback.from_user.id, page)

# Admin handlers
@dp.message(F.text.in_(["👨‍💼 Admin panel", "👨‍💼 Админ панель"]))
async def admin_panel_handler(message: Message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    await message.answer(
        "👨‍💼 Admin paneli",
        reply_markup=get_admin_keyboard(user_id)
    )

@dp.message(F.text.in_(["➕ Mashina qo'shish", "➕ Добавить машину"]))
async def add_car_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    await state.set_state(AddCarStates.waiting_for_photo)
    await message.answer(
        "📷 Mashina rasmini yuboring:",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(StateFilter(AddCarStates.waiting_for_photo), F.photo)
async def process_car_photo(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Create photos directory if it doesn't exist
    photos_dir = os.path.join(os.path.expanduser('~'), 'photos')
    os.makedirs(photos_dir, exist_ok=True)
    
    photo = message.photo[-1]
    file_id = photo.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"car_{timestamp}.jpg"
    full_path = os.path.join(photos_dir, filename)
    
    # Download the photo
    await bot.download_file(file_path, full_path)
    
    await state.update_data(photo_path=full_path)
    await state.set_state(AddCarStates.waiting_for_name)
    
    await message.answer("✏️ Mashina nomini kiriting:")

@dp.message(StateFilter(AddCarStates.waiting_for_name))
async def process_car_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddCarStates.waiting_for_description)
    
    await message.answer("📝 Mashina tavsifini kiriting:")

@dp.message(StateFilter(AddCarStates.waiting_for_description))
async def process_car_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddCarStates.waiting_for_price)
    
    await message.answer("💰 Mashina narxini kiriting (so'mda):")

@dp.message(StateFilter(AddCarStates.waiting_for_price))
async def process_car_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(',', ''))
        await state.update_data(price=price)
        await state.set_state(AddCarStates.waiting_for_type)
        
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="💰 Naqd"), 
                 KeyboardButton(text="💳 Kredit")]
            ],
            resize_keyboard=True
        )
        
        await message.answer("💵 To'lov turini tanlang:", reply_markup=keyboard)
    except ValueError:
        await message.answer("⚠️ Iltimos, raqam kiriting!")

@dp.message(StateFilter(AddCarStates.waiting_for_type), 
           F.text.in_(["💰 Naqd", "💳 Kredit"]))
async def process_car_type(message: Message, state: FSMContext):
    car_type = 'cash' if message.text == "💰 Naqd" else 'credit'
    await state.update_data(car_type=car_type)
    
    if car_type == 'credit':
        await state.set_state(AddCarStates.waiting_for_credit_months)
        await message.answer(
            "📅 Kredit muddatini oylarda kiriting (masalan: 12, 24, 36):",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await state.set_state(AddCarStates.waiting_for_additional_note)
        await message.answer(
            "📝 Qo'shimcha ma'lumot kiriting (agar kerak bo'lsa):",
            reply_markup=ReplyKeyboardRemove()
        )

@dp.message(StateFilter(AddCarStates.waiting_for_credit_months))
async def process_credit_months(message: Message, state: FSMContext):
    try:
        months = int(message.text)
        await state.update_data(credit_months=months)
        await state.set_state(AddCarStates.waiting_for_credit_percent)
        
        await message.answer("📊 Kredit foizini kiriting (masalan: 15, 20):")
    except ValueError:
        await message.answer("⚠️ Iltimos, butun son kiriting!")

@dp.message(StateFilter(AddCarStates.waiting_for_credit_percent))
async def process_credit_percent(message: Message, state: FSMContext):
    try:
        percent = float(message.text)
        await state.update_data(credit_percent=percent)
        await state.set_state(AddCarStates.waiting_for_initial_payment)
        
        await message.answer("💵 Boshlang'ich to'lov miqdorini kiriting (so'mda):")
    except ValueError:
        await message.answer("⚠️ Iltimos, raqam kiriting!")

@dp.message(StateFilter(AddCarStates.waiting_for_initial_payment))
async def process_initial_payment(message: Message, state: FSMContext):
    try:
        payment = float(message.text.replace(',', ''))
        await state.update_data(initial_payment=payment)
        await state.set_state(AddCarStates.waiting_for_credit_note)
        
        await message.answer("📋 Kredit bo'yicha qo'shimcha izoh (agar kerak bo'lsa):")
    except ValueError:
        await message.answer("⚠️ Iltimos, raqam kiriting!")

@dp.message(StateFilter(AddCarStates.waiting_for_credit_note))
async def process_credit_note(message: Message, state: FSMContext):
    await state.update_data(credit_note=message.text)
    await state.set_state(AddCarStates.waiting_for_additional_note)
    
    await message.answer("📝 Qo'shimcha ma'lumot kiriting (agar kerak bo'lsa):")

@dp.message(StateFilter(AddCarStates.waiting_for_additional_note))
async def process_additional_note(message: Message, state: FSMContext):
    await state.update_data(additional_note=message.text)
    await state.set_state(AddCarStates.waiting_for_file)
    
    await message.answer(
        "📎 Agar mashina uchun fayl (PDF, Word, etc.) bo'lsa yuboring, "
        "yoki 'O'tkazib yuborish' tugmasini bosing.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="O'tkazib yuborish")]],
            resize_keyboard=True
        )
    )

@dp.message(StateFilter(AddCarStates.waiting_for_file), 
           F.document | F.text == "O'tkazib yuborish")
async def process_car_file(message: Message, state: FSMContext):
    data = await state.get_data()
    
    if message.document:
        # Create files directory if it doesn't exist
        files_dir = os.path.join(os.path.expanduser('~'), 'files')
        os.makedirs(files_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = message.document.file_name.split('.')[-1]
        filename = f"car_{timestamp}.{ext}"
        full_path = os.path.join(files_dir, filename)
        
        # Download the file
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        await bot.download_file(file_path, full_path)
        
        data['file_path'] = full_path
    else:
        data['file_path'] = None
    
    # Save the car to database
    save_car(data)
    await state.clear()
    
    await message.answer(
        "✅ Mashina muvaffaqiyatli qo'shildi!",
        reply_markup=get_admin_keyboard(message.from_user.id)
    )

# Delete car handlers
@dp.message(F.text.in_(["❌ Mashina o'chirish", "❌ Удалить машину"]))
async def delete_car_start(message: Message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    cars = get_cars()
    
    if not cars:
        await message.answer("❌ O'chirish uchun mashinalar topilmadi")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=car.name, callback_data=f"delete_{car.id}")]
        for car in cars
    ])
    
    await message.answer(
        "❌ O'chirish uchun mashinani tanlang:",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("delete_"))
async def confirm_delete_car(callback: CallbackQuery):
    car_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha", callback_data=f"confirm_delete_{car_id}"),
         InlineKeyboardButton(text="❌ Yo'q", callback_data="cancel_delete")]
    ])
    
    await callback.message.edit_text(
        "⚠️ Bu mashinani rostdan ham o'chirmoqchimisiz?",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("confirm_delete_"))
async def process_delete_car(callback: CallbackQuery):
    car_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Soft delete (mark as inactive)
    cursor.execute("UPDATE cars SET is_active = FALSE WHERE id = ?", (car_id,))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text("✅ Mashina muvaffaqiyatli o'chirildi!")

@dp.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery):
    await callback.message.edit_text("❌ Mashina o'chirilmadi.")

# View applications handler
@dp.message(F.text.in_(["📋 Arizalarni ko'rish", "📋 Посмотреть заявки"]))
async def view_applications_handler(message: Message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT a.*, c.name as car_name, u.full_name as user_name 
    FROM applications a
    JOIN cars c ON a.car_id = c.id
    JOIN users u ON a.user_id = u.user_id
    ORDER BY a.created_at DESC
    LIMIT 20
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        await message.answer("📋 Hozircha arizalar mavjud emas")
        return
    
    for row in rows:
        app = Application(
            id=row[0], user_id=row[1], car_id=row[2],
            user_comment=row[3], phone_number=row[4],
            status=row[5], created_at=row[6],
            car_name=row[7], user_name=row[8]
        )
        
        lang = get_user_language(app.user_id)
        status_text = TEXTS[lang][app.status]
        
        message_text = f"📋 **Ariza #{app.id}**\n\n"
        message_text += f"👤 Foydalanuvchi: {app.user_name}\n"
        message_text += f"🚗 Mashina: {app.car_name}\n"
        message_text += f"📝 Izoh: {app.user_comment}\n"
        message_text += f"📞 Telefon: {app.phone_number}\n"
        message_text += f"📅 Sana: {app.created_at}\n"
        message_text += f"📊 Holat: {status_text}\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{app.id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{app.id}")
            ]
        ])
        
        await message.answer(message_text, reply_markup=keyboard)

@dp.callback_query(F.data.startswith(("approve_", "reject_")))
async def process_application_status(callback: CallbackQuery):
    action = callback.data.split("_")[0]
    app_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if action == "approve":
        cursor.execute("UPDATE applications SET status = 'approved' WHERE id = ?", (app_id,))
        status_text = "✅ Tasdiqlandi"
    else:
        cursor.execute("UPDATE applications SET status = 'rejected' WHERE id = ?", (app_id,))
        status_text = "❌ Rad etildi"
    
    conn.commit()
    
    # Get application info to notify user
    cursor.execute('''
    SELECT a.user_id, c.name, u.language 
    FROM applications a
    JOIN cars c ON a.car_id = c.id
    JOIN users u ON a.user_id = u.user_id
    WHERE a.id = ?
    ''', (app_id,))
    
    app_info = cursor.fetchone()
    conn.close()
    
    if app_info:
        user_id_to_notify = app_info[0]
        car_name = app_info[1]
        lang = app_info[2]
        
        status_user_text = TEXTS[lang]['approved'] if action == "approve" else TEXTS[lang]['rejected']
        
        try:
            await bot.send_message(
                user_id_to_notify,
                f"📢 Sizning arizangiz yangilandi!\n\n"
                f"🚗 Mashina: {car_name}\n"
                f"📊 Yangi holat: {status_user_text}"
            )
        except Exception as e:
            logging.error(f"Error notifying user: {e}")
    
    await callback.message.edit_text(
        f"{status_text}\n\n"
        f"Ariza ID: {app_id}"
    )

# Edit car handlers
@dp.message(F.text.in_(["✏️ Tahrirlash", "✏️ Редактировать"]))
async def edit_car_start(message: Message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    cars = get_cars()
    
    if not cars:
        await message.answer("❌ Tahrirlash uchun mashinalar topilmadi")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=car.name, callback_data=f"edit_{car.id}")]
        for car in cars
    ])
    
    await message.answer(
        "✏️ Tahrirlash uchun mashinani tanlang:",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("edit_"))
async def select_edit_option(callback: CallbackQuery, state: FSMContext):
    car_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    await state.update_data(car_id=car_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Nom", callback_data="edit_name")],
        [InlineKeyboardButton(text="📝 Tavsif", callback_data="edit_description")],
        [InlineKeyboardButton(text="💰 Narx", callback_data="edit_price")],
        [InlineKeyboardButton(text="📷 Rasm", callback_data="edit_photo")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="cancel_edit")]
    ])
    
    await callback.message.edit_text(
        "✏️ Nimalarni tahrirlamoqchisiz?",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "edit_name")
async def edit_car_name_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditCarStates.waiting_for_new_name)
    await callback.message.edit_text("✏️ Yangi nom kiriting:")

@dp.message(StateFilter(EditCarStates.waiting_for_new_name))
async def process_new_name(message: Message, state: FSMContext):
    data = await state.get_data()
    car_id = data['car_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE cars SET name = ? WHERE id = ?", (message.text, car_id))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(
        "✅ Mashina nomi muvaffaqiyatli yangilandi!",
        reply_markup=get_admin_keyboard(message.from_user.id)
    )

@dp.callback_query(F.data == "edit_description")
async def edit_car_description_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditCarStates.waiting_for_new_description)
    await callback.message.edit_text("📝 Yangi tavsif kiriting:")

@dp.message(StateFilter(EditCarStates.waiting_for_new_description))
async def process_new_description(message: Message, state: FSMContext):
    data = await state.get_data()
    car_id = data['car_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE cars SET description = ? WHERE id = ?", (message.text, car_id))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(
        "✅ Mashina tavsifi muvaffaqiyatli yangilandi!",
        reply_markup=get_admin_keyboard(message.from_user.id)
    )

@dp.callback_query(F.data == "edit_price")
async def edit_car_price_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditCarStates.waiting_for_new_price)
    await callback.message.edit_text("💰 Yangi narx kiriting (so'mda):")

@dp.message(StateFilter(EditCarStates.waiting_for_new_price))
async def process_new_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(',', ''))
        data = await state.get_data()
        car_id = data['car_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE cars SET price = ? WHERE id = ?", (price, car_id))
        conn.commit()
        conn.close()
        
        await state.clear()
        await message.answer(
            "✅ Mashina narxi muvaffaqiyatli yangilandi!",
            reply_markup=get_admin_keyboard(message.from_user.id)
        )
    except ValueError:
        await message.answer("⚠️ Iltimos, raqam kiriting!")

@dp.callback_query(F.data == "edit_photo")
async def edit_car_photo_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditCarStates.waiting_for_new_photo)
    await callback.message.edit_text("📷 Yangi rasm yuboring:")

@dp.message(StateFilter(EditCarStates.waiting_for_new_photo), F.photo)
async def process_new_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    car_id = data['car_id']
    
    # Create photos directory if it doesn't exist
    photos_dir = os.path.join(os.path.expanduser('~'), 'photos')
    os.makedirs(photos_dir, exist_ok=True)
    
    photo = message.photo[-1]
    file_id = photo.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"car_{timestamp}.jpg"
    full_path = os.path.join(photos_dir, filename)
    
    # Download the photo
    await bot.download_file(file_path, full_path)
    
    # Update database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE cars SET photo_path = ? WHERE id = ?", (full_path, car_id))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(
        "✅ Mashina rasmi muvaffaqiyatli yangilandi!",
        reply_markup=get_admin_keyboard(message.from_user.id)
    )

@dp.callback_query(F.data == "cancel_edit")
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Tahrirlash bekor qilindi.")

# Back button handler
@dp.message(F.text.in_(["🔙 Orqaga", "🔙 Назад"]))
async def back_handler(message: Message):
    user_id = message.from_user.id
    await message.answer(
        get_text(user_id, 'main_menu'),
        reply_markup=get_main_keyboard(user_id)
    )

# Webhook setup
async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)
    logging.info("Bot started")

# Main function
async def main():
    # Initialize database
    init_db()
    
    # Create directories
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    os.makedirs(FILES_DIR, exist_ok=True)
    
    # Set webhook
    await bot.set_webhook(url=WEBHOOK_URL)
    
    # Start web app
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    
    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped!")
