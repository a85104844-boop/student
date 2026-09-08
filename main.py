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
            is_approved INTEGER DEFAULT 0
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
        INSERT OR REPLACE INTO users (user_id, full_name, gender, target_gender, university, course, purpose, bio, photo_id, is_approved)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (user_id, data['name'], data['gender'], data['target_gender'], data['university'], data['course'], data['purpose'], data['bio'], data['photo_id']))
    conn.commit()
    conn.close()

def approve_user_in_db(user_id):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_approved = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_next_candidate(user_id, target_gender):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    
    if "Yigit" in target_gender:
        cursor.execute("""
            SELECT * FROM users 
            WHERE is_approved = 1 
              AND user_id != ? 
              AND gender = 'Yigit'
              AND user_id NOT IN (SELECT to_user FROM likes WHERE from_user = ?)
            ORDER BY RANDOM() LIMIT 1
        """, (user_id, user_id))
    elif "Qiz" in target_gender:
        cursor.execute("""
            SELECT * FROM users 
            WHERE is_approved = 1 
              AND user_id != ? 
              AND gender = 'Qiz'
              AND user_id NOT IN (SELECT to_user FROM likes WHERE from_user = ?)
            ORDER BY RANDOM() LIMIT 1
        """, (user_id, user_id))
    else:
        cursor.execute("""
            SELECT * FROM users 
            WHERE is_approved = 1 
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

# ==================== FSM STATES ====================
class Registration(StatesGroup):
    name = State()
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

# ==================== PROFILE & MATCHING ====================

@dp.message(F.text == "👤 Mening profilim")
async def show_my_profile(message: types.Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Siz hali ro'yxatdan o'tmadingiz. /start bosing.")
        return
        
    status = "✅ Tasdiqlangan" if user[9] == 1 else "⏳ Kutilmoqda"
    caption = (
        f"📋 **Sizning profilingiz:**\n\n"
        f"👤 Ism: {user[1]}\n"
        f"🔹 Jinsingiz: {user[2]}\n"
        f"🎯 Qidiryapsiz: {user[3]}\n"
        f"🎓 Universitet: {user[4]} ({user[5]})\n"
        f"📌 Maqsad: {user[6]}\n"
        f"📝 Bio: {user[7]}\n"
        f"Holat: {status}"
    )
    edit_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Anketani qayta to'ldirish", callback_data="re_register")]
    ])
    await message.answer_photo(photo=user[8], caption=caption, reply_markup=edit_kb, parse_mode="Markdown")

@dp.callback_query(F.data == "re_register")
async def handle_re_register(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("Ismingizni kiriting:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.name)
    await callback.answer()

@dp.message(F.text == "🔍 Anketalarni ko'rish")
async def browse_candidates(message: types.Message):
    user = get_user(message.from_user.id)
    if not user or user[9] != 1:
        await message.answer("Anketalarni ko'rish uchun avval profilingiz admin tomonidan tasdiqlanishi kerak.")
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
    _, action, target_id = callback.data.split("_")
    target_id = int(target_id)
    from_id = callback.from_user.id
    
    is_match = save_action(from_id, target_id, action)
    await callback.message.delete()
    
    # Agar like bosilgan bo'lsa va hali o'zaro match bo'lmasa - target userga xabar beramiz
    if action == "like" and not is_match:
        try:
            await bot.send_message(
                chat_id=target_id, 
                text="🔔 **Kimdir sizga like bosdi!**\n\nKimligini bilish uchun 'Anketalarni ko'rish' tugmasini bosing 👀",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    # Agar o'zaro match bo'lsa
    if is_match and action == "like":
        candidate = get_user(target_id)  # target user ma'lumotlari
        current = get_user(from_id)    # hozirgi user ma'lumotlari
        
        # 1-userga 2-userning profilini yuboramiz
        caption_for_current = (
            f"🔥 **O'zaro moslik (Match)!**\n\n"
            f"Siz va [{candidate[1]}](tg://user?id={target_id}) bir-biringizga like bosdingiz!\n\n"
            f"🎓 Ism: {candidate[1]}\n"
            f"🏛 Universitet: {candidate[4]} ({candidate[5]})\n"
            f"📌 Maqsad: {candidate[6]}\n"
            f"📝 Bio: {candidate[7]}\n\n"
            f"💬 Bog'lanish: [Profilga o'tish](tg://user?id={target_id})"
        )
        try:
            await bot.send_photo(chat_id=from_id, photo=candidate[8], caption=caption_for_current, parse_mode="Markdown")
        except Exception:
            pass

        # 2-userga 1-userning profilini yuboramiz
        caption_for_target = (
            f"🔥 **O'zaro moslik (Match)!**\n\n"
            f"Siz va [{current[1]}](tg://user?id={from_id}) bir-biringizga like bosdingiz!\n\n"
            f"🎓 Ism: {current[1]}\n"
            f"🏛 Universitet: {current[4]} ({current[5]})\n"
            f"📌 Maqsad: {current[6]}\n"
            f"📝 Bio: {current[7]}\n\n"
            f"💬 Bog'lanish: [Profilga o'tish](tg://user?id={from_id})"
        )
        try:
            await bot.send_photo(chat_id=target_id, photo=current[8], caption=caption_for_target, parse_mode="Markdown")
        except Exception:
            pass
        
    # Keyingi anketani ko'rsatish
    user = get_user(from_id)
    next_candidate = get_next_candidate(from_id, user[3])
    
    if next_candidate:
        match_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👎 O'tkazish", callback_data=f"act_dislike_{next_candidate[0]}"),
                InlineKeyboardButton(text="❤️ Like", callback_data=f"act_like_{next_candidate[0]}")
            ]
        ])
        caption = (
            f"🎓 **{next_candidate[1]}**\n\n"
            f"🏛 Universitet: {next_candidate[4]} ({next_candidate[5]})\n"
            f"🎯 Maqsad: {next_candidate[6]}\n"
            f"📝 Bio: {next_candidate[7]}"
        )
        await callback.message.answer_photo(photo=next_candidate[8], caption=caption, reply_markup=match_kb, parse_mode="Markdown")
    else:
        await callback.message.answer("Boshqa yangi anketalar qolmadi!")
    
    await callback.answer()

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
    
