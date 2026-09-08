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

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID_RAW = os.environ.get("ADMIN_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi!")

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
            full_name TEXT,
            gender TEXT,
            target_gender TEXT,
            university TEXT,
            course TEXT,
            purpose TEXT,
            bio TEXT,
            photo_id TEXT,
            is_approved INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            from_user INTEGER,
            to_user INTEGER,
            action TEXT,
            PRIMARY KEY (from_user, to_user)
        )
    """)
    conn.commit()
    conn.close()

init_db()

def save_user(user_id, data):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, full_name, gender, target_gender, university, course, purpose, bio, photo_id, is_approved, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1)
    """, (user_id, data['name'], data['gender'], data['target_gender'], data['university'], data['course'], data['purpose'], data['bio'], data['photo_id']))
    conn.commit()
    conn.close()

def approve_user_in_db(user_id):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_approved = 1, is_active = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def update_user_status(user_id, is_active):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_active = ? WHERE user_id = ?", (is_active, user_id))
    conn.commit()
    conn.close()

def delete_user_from_db(user_id):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM likes WHERE from_user = ? OR to_user = ?", (user_id, user_id))
    conn.commit()
    conn.close()

def get_next_candidate(user_id, target_gender):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    
    if "Yigit" in target_gender:
        cursor.execute("""
            SELECT * FROM users 
            WHERE is_approved = 1 
              AND is_active = 1
              AND user_id != ? 
              AND gender = 'Yigit'
              AND user_id NOT IN (SELECT to_user FROM likes WHERE from_user = ?)
            ORDER BY RANDOM() LIMIT 1
        """, (user_id, user_id))
    elif "Qiz" in target_gender:
        cursor.execute("""
            SELECT * FROM users 
            WHERE is_approved = 1 
              AND is_active = 1
              AND user_id != ? 
              AND gender = 'Qiz'
              AND user_id NOT IN (SELECT to_user FROM likes WHERE from_user = ?)
            ORDER BY RANDOM() LIMIT 1
        """, (user_id, user_id))
    else:
        cursor.execute("""
            SELECT * FROM users 
            WHERE is_approved = 1 
              AND is_active = 1
              AND user_id != ? 
              AND user_id NOT IN (SELECT to_user FROM likes WHERE from_user = ?)
            ORDER BY RANDOM() LIMIT 1
        """, (user_id, user_id))
        
    candidate = cursor.fetchone()
    conn.close()
    return candidate

def save_action(from_user, to_user, action):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO likes (from_user, to_user, action) VALUES (?, ?, ?)", (from_user, to_user, action))
    conn.commit()
    
    cursor.execute("SELECT action FROM likes WHERE from_user = ? AND to_user = ?", (to_user, from_user))
    match = cursor.fetchone()
    conn.close()
    return match and match[0] == "like"

# ==================== KEYBOARDS ====================
def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Anketalarni ko'rish"), KeyboardButton(text="👤 Mening profilim")]
        ],
        resize_keyboard=True
    )

def universities_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="TATU", callback_data="uni_TATU"),
            InlineKeyboardButton(text="O'zMU", callback_data="uni_UzMU")
        ],
        [
            InlineKeyboardButton(text="TDTU (Politeh)", callback_data="uni_TDTU"),
            InlineKeyboardButton(text="TDIU (Narxoz)", callback_data="uni_TDIU")
        ],
        [
            InlineKeyboardButton(text="TDYU (Yuridik)", callback_data="uni_TDYU"),
            InlineKeyboardButton(text="TMI (Moliya)", callback_data="uni_TMI")
        ],
        [
            InlineKeyboardButton(text="TDPU (Pedagogika)", callback_data="uni_TDPU"),
            InlineKeyboardButton(text="TDSI (Stomatologiya)", callback_data="uni_TDSI")
        ],
        [
            InlineKeyboardButton(text="JIDU", callback_data="uni_JIDU"),
            InlineKeyboardButton(text="O'zJOKU", callback_data="uni_UzJOKU")
        ],
        [
            InlineKeyboardButton(text="TIIIMX (Irrigatsiya)", callback_data="uni_Irrigatsiya"),
            InlineKeyboardButton(text="Farmatsevtika instituti", callback_data="uni_Farmi")
        ],
        [
            InlineKeyboardButton(text="TAQI (Arxitektura)", callback_data="uni_TAQI"),
            InlineKeyboardButton(text="TAYI (Transport/Avto)", callback_data="uni_TAYI")
        ],
        [
            InlineKeyboardButton(text="O'XIA (Islom akademiya)", callback_data="uni_OXIA"),
            InlineKeyboardButton(text="TTA / TSDI", callback_data="uni_TTA")
        ],
        [
            InlineKeyboardButton(text="✏️ Boshqa universitet", callback_data="uni_other")
        ]
    ])

# ==================== FSM STATES ====================
class Registration(StatesGroup):
    name = State()
    gender = State()
    target_gender = State()
    university = State()
    custom_university = State()
    course = State()
    purpose = State()
    bio = State()
    photo = State()
    verification_photo = State()

# ==================== HANDLERS ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = get_user(message.from_user.id)
    
    if user and user[9] == 1:
        await message.answer("Asosiy menyu:", reply_markup=main_menu_kb())
        return

    await message.answer("Salom! Student Social Network botiga xush kelibsiz.\n\nIsmingizni kiriting:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.name)

@dp.message(Registration.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Yigit"), KeyboardButton(text="Qiz")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Jinsingizni tanlang:", reply_markup=kb)
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
    await message.answer("Qaysi Universitetda o'qiysiz? Quyidagilardan birini tanlang:", reply_markup=universities_kb())
    await state.set_state(Registration.university)

@dp.callback_query(F.data.startswith("uni_"))
async def process_university_callback(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != Registration.university.state:
        await callback.answer()
        return

    uni_code = callback.data.split("_")[1]
    
    if uni_code == "other":
        await callback.message.edit_text("Universitetingiz nomini matn ko'rinishida yozib yuboring:")
        await state.set_state(Registration.custom_university)
        await callback.answer()
        return

    uni_names = {
        "TATU": "TATU",
        "UzMU": "O'zMU",
        "TDTU": "TDTU",
        "TDIU": "TDIU",
        "TDYU": "TDYU",
        "TMI": "TMI",
        "TDPU": "TDPU",
        "TDSI": "TDSI",
        "JIDU": "JIDU",
        "UzJOKU": "O'zJOKU",
        "Irrigatsiya": "TIIIMX",
        "Farmi": "Farmatsevtika instituti",
        "TAQI": "TAQI",
        "TAYI": "TAYI",
        "OXIA": "O'XIA",
        "TTA": "TTA"
    }
    selected_uni = uni_names.get(uni_code, "Boshqa")
    await state.update_data(university=selected_uni)
    
    try:
        await callback.message.delete()
    except Exception:
        pass

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1-kurs"), KeyboardButton(text="2-kurs")],
            [KeyboardButton(text="3-kurs"), KeyboardButton(text="4-kurs")],
            [KeyboardButton(text="Magistr")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await bot.send_message(
        chat_id=callback.from_user.id,
        text=f"Tanlangan OTM: <b>{selected_uni}</b>\n\nNechanchi kursda o'qiysiz?",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.set_state(Registration.course)
    await callback.answer()

@dp.message(Registration.custom_university)
async def process_custom_university(message: types.Message, state: FSMContext):
    uni_name = message.text.strip()
    await state.update_data(university=uni_name)
    
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1-kurs"), KeyboardButton(text="2-kurs")],
            [KeyboardButton(text="3-kurs"), KeyboardButton(text="4-kurs")],
            [KeyboardButton(text="Magistr")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(f"Universitet: <b>{uni_name}</b>\n\nNechanchi kursda o'qiysiz?", reply_markup=kb, parse_mode="HTML")
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
    
    save_user(message.from_user.id, data)
    
    await message.answer("Anketangiz adminga yuborildi. Tasdiqlangach xabar beramiz!", reply_markup=ReplyKeyboardRemove())
    
    if ADMIN_ID:
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{message.from_user.id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{message.from_user.id}")
            ]
        ])
        
        caption = (
            f"🆕 Yangi anketa!\n\n"
            f"👤 ID: {message.from_user.id}\n"
            f"👤 Ism: {data['name']}\n"
            f"🔹 Jinsi: {data['gender']}\n"
            f"🎯 Qidiryapti: {data['target_gender']}\n"
            f"🎓 OTM: {data['university']} ({data['course']})\n"
            f"📌 Maqsad: {data['purpose']}\n"
            f"📝 Bio: {data['bio']}"
        )
        
        try:
            await bot.send_photo(chat_id=ADMIN_ID, photo=data['photo_id'], caption=caption)
            await bot.send_photo(
                chat_id=ADMIN_ID, 
                photo=verify_photo_id, 
                caption=f"✌️ Selfi verifikatsiya (User ID: {message.from_user.id})", 
                reply_markup=admin_kb
            )
        except Exception as e:
            logging.error(f"Adminga xatolik: {e}")
            
    await state.clear()

# ==================== ADMIN CALLBACKS ====================

@dp.callback_query(F.data.startswith("approve_"))
async def approve_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    approve_user_in_db(user_id)
    
    try:
        await bot.send_message(
            chat_id=user_id, 
            text="🎉 Tabriklaymiz! Anketangiz tasdiqlandi. Quyidagi menyu orqali anketalarni ko'rishingiz mumkin:", 
            reply_markup=main_menu_kb()
        )
    except Exception:
        pass
        
    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ TASDIQLANDI")
    await callback.answer("Foydalanuvchi tasdiqlandi!")

@dp.callback_query(F.data.startswith("reject_"))
async def reject_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    try:
        await bot.send_message(chat_id=user_id, text="❌ Afsuski, anketangiz admin tomonidan rad etildi. Qaytadan /start bosing.")
    except Exception:
        pass
        
    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ RAD ETILDI")
    await callback.answer("Anketa rad etildi!")

# ==================== PROFILE & SETTINGS ====================

@dp.message(F.text == "👤 Mening profilim")
async def show_my_profile(message: types.Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Siz hali ro'yxatdan o'tmadingiz. /start bosing.")
        return
        
    status_text = "✅ Tasdiqlangan" if user[9] == 1 else "⏳ Kutilmoqda"
    active_status = "🟢 Qidiruvda faol" if user[10] == 1 else "⏸ Muzlatilgan (Yashiringan)"
    
    caption = (
        f"📋 **Sizning profilingiz:**\n\n"
        f"👤 Ism: {user[1]}\n"
        f"🔹 Jinsingiz: {user[2]}\n"
        f"🎯 Qidiryapsiz: {user[3]}\n"
        f"🎓 Universitet: {user[4]} ({user[5]})\n"
        f"📌 Maqsad: {user[6]}\n"
        f"📝 Bio: {user[7]}\n"
        f"Holat: {status_text} | {active_status}"
    )
    
    pause_btn_text = "⏸ Anketani muzlatish" if user[10] == 1 else "▶️ Anketani yoqish"
    pause_callback = "pause_profile" if user[10] == 1 else "activate_profile"

    edit_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Anketani qayta to'ldirish", callback_data="re_register")],
        [InlineKeyboardButton(text=pause_btn_text, callback_data=pause_callback)],
        [InlineKeyboardButton(text="❌ Anketani o'chirish", callback_data="delete_profile")]
    ])
    await message.answer_photo(photo=user[8], caption=caption, reply_markup=edit_kb, parse_mode="Markdown")

@dp.callback_query(F.data == "re_register")
async def handle_re_register(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("Ismingizni kiriting:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.name)
    await callback.answer()

@dp.callback_query(F.data == "pause_profile")
async def handle_pause(callback: types.CallbackQuery):
    update_user_status(callback.from_user.id, 0)
    await callback.answer("Anketangiz muzlatildi (boshqalarga ko'rinmaydi).")
    await callback.message.delete()
    await show_my_profile(callback.message)

@dp.callback_query(F.data == "activate_profile")
async def handle_activate(callback: types.CallbackQuery):
    update_user_status(callback.from_user.id, 1)
    await callback.answer("Anketangiz faollashdi!")
    await callback.message.delete()
    await show_my_profile(callback.message)

@dp.callback_query(F.data == "delete_profile")
async def handle_delete(callback: types.CallbackQuery):
    delete_user_from_db(callback.from_user.id)
    await callback.message.delete()
    await callback.message.answer("Anketangiz o'chirib yuborildi. Qaytadan boshlash uchun /start bosing.", reply_markup=ReplyKeyboardRemove())
    await callback.answer()

@dp.message(F.text == "🔍 Anketalarni ko'rish")
async def browse_candidates(message: types.Message):
    user = get_user(message.from_user.id)
    if not user or user[9] != 1:
        await message.answer("Anketalarni ko'rish uchun avval profilingiz admin tomonidan tasdiqlanishi kerak.")
        return
        
    if user[10] == 0:
        await message.answer("Sizning anketangiz muzlatilgan. Anketalarni ko'rish uchun avval profilingizdan uni yoqing.")
        return
        
    candidate = get_next_candidate(message.from_user.id, user[3])
    if not candidate:
        await message.answer("Hozircha sizga mos yangi anketalar mavjud emas. Birozdan so'ng qayta urinib ko'ring!")
        return
        
    match_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👎 O'tkazish", callback_data=f"act_dislike_{candidate[0]}"),
            InlineKeyboardButton(text="❤️ Like", callback_data=f"act_like_{candidate[0]}")
        ]
    ])
    
    caption = (
        f"🎓 **{candidate[1]}**\n\n"
        f"🏛 Universitet: {candidate[4]} ({candidate[5]})\n"
        f"🎯 Maqsad: {candidate[6]}\n"
        f"📝 Bio: {candidate[7]}"
    )
    await message.answer_photo(photo=candidate[8], caption=caption, reply_markup=match_kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("act_"))
async def handle_match_action(callback: types.CallbackQuery):
    _,
