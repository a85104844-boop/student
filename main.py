import asyncio
import logging
import os
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiohttp import web

# Logging
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID_RAW = os.environ.get("ADMIN_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! Render Environment Variables bo'limini tekshiring.")

# Admin ID ni xavfsiz aylantirish
try:
    ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW else None
except ValueError:
    ADMIN_ID = None

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ==================== DATABASE (SQLite) ====================
def init_db():
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            gender TEXT,
            target_gender TEXT,
            university TEXT,
            course TEXT,
            purpose TEXT,
            bio TEXT,
            photo_id TEXT,
            is_approved INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

def save_user(user_id, data):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, gender, target_gender, university, course, purpose, bio, photo_id, is_approved)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (user_id, data['gender'], data['target_gender'], data['university'], data['course'], data['purpose'], data['bio'], data['photo_id']))
    conn.commit()
    conn.close()

def approve_user_in_db(user_id):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_approved = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Main menu keyboard
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Anketalarni ko'rish"), KeyboardButton(text="👤 Im im profilim")]
        ],
        resize_keyboard=True
    )

# ==================== FSM STATES ====================
class Registration(StatesGroup):
    gender = State()
    target_gender = State()
    university = State()
    course = State()
    purpose = State()
    bio = State()
    photo = State()
    verification_photo = State()

# ==================== HANDLERS ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Yigit"), KeyboardButton(text="Qiz")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Salom! Student Social Network botiga xush kelibsiz.\n\nJinsingizni tanlang:", reply_markup=kb)
    await state.set_state(Registration.gender)

@dp.message(Registration.gender)
async def process_gender(message: types.Message, state: FSMContext):
    await state.update_data(gender=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Yigitlar"), KeyboardButton(text="Qizlar")], [KeyboardButton(text="Farqi yo'q")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Kimlar bilan tanishmoqchisiz?", reply_markup=kb)
    await state.set_state(Registration.target_gender)

@dp.message(Registration.target_gender)
async def process_target_gender(message: types.Message, state: FSMContext):
    await state.update_data(target_gender=message.text)
    await message.answer("Qaysi Universitetda o'qiysiz? (masalan: TDTU, TATU, NUUz)", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.university)

@dp.message(Registration.university)
async def process_university(message: types.Message, state: FSMContext):
    await state.update_data(university=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1-kurs"), KeyboardButton(text="2-kurs")],
            [KeyboardButton(text="3-kurs"), KeyboardButton(text="4-kurs")],
            [KeyboardButton(text="Magistr")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Nechanchi kursda o'qiysiz?", reply_markup=kb)
    await state.set_state(Registration.course)

@dp.message(Registration.course)
async def process_course(message: types.Message, state: FSMContext):
    await state.update_data(course=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Munosabat"), KeyboardButton(text="Do'stlashish")],
            [KeyboardButton(text="Birga o'qish (Study Buddy)")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Asosiy maqsadingiz nima?", reply_markup=kb)
    await state.set_state(Registration.purpose)

@dp.message(Registration.purpose)
async def process_purpose(message: types.Message, state: FSMContext):
    await state.update_data(purpose=message.text)
    await message.answer("O'zingiz haqida qisqacha yozing (Bio):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.bio)

@dp.message(Registration.bio)
async def process_bio(message: types.Message, state: FSMContext):
    await state.update_data(bio=message.text)
    await message.answer("Anketa uchun rasmingizni yuboring:")
    await state.set_state(Registration.photo)

@dp.message(Registration.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    
    await message.answer(
        "Verifikatsiya bosqichi:\n\n"
        "Soxta anketalarning oldini olish uchun, qo'lingiz bilan Victory (✌️) "
        "ishorasini ko'rsatgan selfi rasmingizni yuboring."
    )
    await state.set_state(Registration.verification_photo)

@dp.message(Registration.verification_photo, F.photo)
async def process_verification_photo(message: types.Message, state: FSMContext):
    verify_photo_id = message.photo[-1].file_id
    data = await state.get_data()
    
    # Bazaga saqlaymiz
    save_user(message.from_user.id, data)
    
    await message.answer("Anketangiz adminga yuborildi. Tasdiqlangach xabar beramiz!", reply_markup=get_main_keyboard())
    
    # Adminga yuborish
    if ADMIN_ID:
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{message.from_user.id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{message.from_user.id}")
            ]
        ])
        
        caption = (
            f"🆕 **Yangi anketa!**\n\n"
            f"👤 ID: {message.from_user.id}\n"
            f"👤 Ism: {message.from_user.full_name}\n"
            f"🔹 Jinsi: {data['gender']}\n"
            f"🎯 Qidiryapti: {data['target_gender']}\n"
            f"🎓 OTM: {data['university']} ({data['course']})\n"
            f"📌 Maqsad: {data['purpose']}\n"
            f"📝 Bio: {data['bio']}"
        )
        
        try:
            # Anketa rasmi va ma'lumotlari
            await bot.send_photo(chat_id=ADMIN_ID, photo=data['photo_id'], caption=caption)
            # Selfi verifikatsiya rasmi
            await bot.send_photo(
                chat_id=ADMIN_ID, 
                photo=verify_photo_id, 
                caption=f"✌️ Selfi verifikatsiya (User ID: {message.from_user.id})", 
                reply_markup=admin_kb
            )
        except Exception as e:
            logging.error(f"Adminga xabar yuborishda xato: {e}")
            
    await state.clear()

# ==================== ADMIN CALLBACKS ====================

@dp.callback_query(F.data.startswith("approve_"))
async def approve_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    approve_user_in_db(user_id)
    
    try:
        await bot.send_message(chat_id=user_id, text="🎉 Tabriklaymiz! Anketangiz tasdiqlandi. Endi botdan foydalanishingiz mumkin.", reply_markup=get_main_keyboard())
    except Exception:
        pass
        
    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ **TASDIQLANDI**")
    await callback.answer("Foydalanuvchi tasdiqlandi!")

@dp.callback_query(F.data.startswith("reject_"))
async def reject_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    
    try:
        await bot.send_message(chat_id=user_id, text="❌ Afsuski, anketangiz admin tomonidan rad etildi. Qaytadan /start bosing.")
    except Exception:
        pass
        
    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ **RAD ETILDI**")
    await callback.answer("Anketa rad etildi!")

# ==================== HEALTH CHECK WEB SERVER ====================
async def handle(request):
    return web.Response(text="Bot runs 24/7 on Render!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    asyncio.create_task(start_web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
