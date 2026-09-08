import asyncio
import logging
import sqlite3
import json
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, 
    CallbackQuery, 
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardRemove
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8894028288:AAG70cJSclXr5YkKZTp0R8MumRDgpf_wnR8"
ADMIN_ID = 8837587182

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

def init_db():
    conn = sqlite3.connect("student_network.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            age INTEGER,
            gender TEXT,
            target_gender TEXT,
            university TEXT,
            course TEXT,
            purpose TEXT,
            interests TEXT,
            bio TEXT,
            photo_id TEXT,
            is_verified INTEGER DEFAULT 0,
            is_blocked INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            from_user_id INTEGER,
            to_user_id INTEGER,
            action TEXT,
            PRIMARY KEY (from_user_id, to_user_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_chats (
            user_id INTEGER PRIMARY KEY,
            partner_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

UNIVERSITIES = ["TATU", "TDTU", "O'zMU", "TDYU", "TDIU", "AMITY", "WIUT", "INHA", "TMA", "Boshqa"]
COURSES = ["1-kurs", "2-kurs", "3-kurs", "4-kurs", "Magistr"]
PURPOSES = ["Munosabat", "Do'stlik", "Suhbatdosh", "Yangi tanishlar"]
INTEREST_OPTIONS = ["Musiqa", "Gaming", "Sport", "Kitob", "Kino", "IT", "Sayohat", "Art", "Gym"]

class Registration(StatesGroup):
    terms = State()
    full_name = State()
    age = State()
    gender = State()
    target_gender = State()
    university = State()
    course = State()
    purpose = State()
    interests = State()
    bio = State()
    photo = State()
    verification = State()

def terms_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Qoidalarga roziman (18+)", callback_data="accept_terms")]
    ])

def build_reply_keyboard(items):
    buttons = [[KeyboardButton(text=item)] for item in items]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

def interests_keyboard(selected_list):
    buttons = []
    row = []
    for item in INTEREST_OPTIONS:
        text = f"[X] {item}" if item in selected_list else item
        row.append(InlineKeyboardButton(text=text, callback_data=f"toggle_interest_{item}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Tayyor (Davom etish)", callback_data="done_interests")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Talabalarni ko'rish")],
            [KeyboardButton(text="Profilim")]
        ],
        resize_keyboard=True
    )

def action_keyboard(target_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Like", callback_data=f"like_{target_id}"),
            InlineKeyboardButton(text="Pass", callback_data=f"pass_{target_id}")
        ]
    ])

def admin_verify_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Tasdiqlash", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton(text="Rad etish", callback_data=f"reject_{user_id}")
        ]
    ])

def chat_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Muloqotni yakunlash")]],
        resize_keyboard=True
    )

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    conn = sqlite3.connect("student_network.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, is_verified FROM users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        if user[1] == 1:
            await message.answer("Toshkent Talabalari Tarmog'iga xush kelibsiz!", reply_markup=main_menu())
        else:
            await message.answer("Anketangiz adminga yuborilgan. Tasdiqlanishini kuting.")
    else:
        terms = "Toshkent Talabalari Social Network\n\nQoidalar:\n1. Faqat Toshkent OTMlari talabalari uchun.\n2. Hurmat va xavfsizlik birinchi o'rinda.\n3. Yoshingiz 18 dan kichik bo'lmasligi lozim."
        await message.answer(terms, reply_markup=terms_keyboard())
        await state.set_state(Registration.terms)

@router.callback_query(Registration.terms, F.data == "accept_terms")
async def accept_terms(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("Ismingizni kiriting:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.full_name)

@router.message(Registration.full_name, F.text)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Yoshingizni kiriting (Masalan: 20):")
    await state.set_state(Registration.age)

@router.message(Registration.age, F.text)
async def process_age(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) < 18 or int(message.text) > 60:
        await message.answer("Iltimos, to'g'ri yosh kiriting (18+):")
        return
    await state.update_data(age=int(message.text))
    await message.answer("Jinsingizni tanlang:", reply_markup=build_reply_keyboard(["Yigit", "Qiz"]))
    await state.set_state(Registration.gender)

@router.message(Registration.gender, F.text)
async def process_gender(message: Message, state: FSMContext):
    if message.text not in ["Yigit", "Qiz"]:
        await message.answer("Tugmalardan birini tanlang:")
        return
    await state.update_data(gender=message.text)
    await message.answer("Kimlar bilan tanishmoqchisiz?", reply_markup=build_reply_keyboard(["Qizlar", "Yigitlar", "Farqi yo'q"]))
    await state.set_state(Registration.target_gender)

@router.message(Registration.target_gender, F.text)
async def process_target_gender(message: Message, state: FSMContext):
    await state.update_data(target_gender=message.text)
    await message.answer("Qaysi Universitetda o'qiysiz?", reply_markup=build_reply_keyboard(UNIVERSITIES))
    await state.set_state(Registration.university)

@router.message(Registration.university, F.text)
async def process_university(message: Message, state: FSMContext):
    await state.update_data(university=message.text)
    await message.answer("Nechanchi kursda o'qiysiz?", reply_markup=build_reply_keyboard(COURSES))
    await state.set_state(Registration.course)

@router.message(Registration.course, F.text)
async def process_course(message: Message, state: FSMContext):
    await state.update_data(course=message.text)
    await message.answer("Asosiy maqsadingiz nima?", reply_markup=build_reply_keyboard(PURPOSES))
    await state.set_state(Registration.purpose)

@router.message(Registration.purpose, F.text)
async def process_purpose(message: Message, state: FSMContext):
    await state.update_data(purpose=message.text, interests=[])
    await message.answer("Qiziqishlaringizni tanlang:", reply_markup=interests_keyboard([]))
    await state.set_state(Registration.interests)

@router.callback_query(Registration.interests, F.data.startswith("toggle_interest_"))
async def toggle_interest(callback: CallbackQuery, state: FSMContext):
    item = callback.data.replace("toggle_interest_", "")
    data = await state.get_data()
    selected = data.get("interests", [])
    if item in selected:
        selected.remove(item)
    else:
        selected.append(item)
    await state.update_data(interests=selected)
    await callback.message.edit_reply_markup(reply_markup=interests_keyboard(selected))

@router.callback_query(Registration.interests, F.data == "done_interests")
async def done_interests(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("O'zingiz haqingizda qisqacha yozing (Bio):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.bio)

@router.message(Registration.bio, F.text)
async def process_bio(message: Message, state: FSMContext):
    await state.update_data(bio=message.text)
    await message.answer("Anketa uchun rasmingizni yuboring:")
    await state.set_state(Registration.photo)

@router.message(Registration.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await message.answer("Verifikatsiya bosqichi:\n\nSoxta anketalarning oldini olish uchun, qo'lingiz bilan Victory ishorasini ko'rsatgan selfi rasmingizni yuboring.")
    await state.set_state(Registration.verification)

@router.message(Registration.verification, F.photo)
async def process_verification(message: Message, state: FSMContext):
    v_photo_id = message.photo[-1].file_id
    data = await state.get_data()
    user_id = message.from_user.id
    
    conn = sqlite3.connect("student_network.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users 
        (user_id, full_name, age, gender, target_gender, university, course, purpose, interests, bio, photo_id, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (
        user_id, data['full_name'], data['age'], data['gender'], data['target_gender'],
        data['university'], data['course'], data['purpose'], json.dumps(data['interests']),
        data['bio'], data['photo_id']
    ))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer("Anketangiz adminga yuborildi. Tasdiqlangach xabar beramiz!")

    caption = f"Yangi Talaba Verifikatsiyasi!\n\nIsm: {data['full_name']}\nYosh: {data['age']} | Jinsi: {data['gender']}\nOTM: {data['university']} ({data['course']})\nMaqsad: {data['purpose']}\nQiziqishlar: {', '.join(data['interests'])}\nBio: {data['bio']}\nID: {user_id}"
    
    try:
        await bot.send_photo(chat_id=ADMIN_ID, photo=v_photo_id, caption=caption, reply_markup=admin_verify_keyboard(user_id))
    except Exception as e:
        logging.error(f"Admin xabari yuborilmadi: {e}")

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect("student_network.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_verified = 0")
    pending_users = cursor.fetchone()[0]
    conn.close()

    await message.answer(f"ADMIN PANEL\n\nJami foydalanuvchilar: {total_users}\nTasdiqlash kutilayotganlar: {pending_users}")

@router.callback_query(F.data.startswith("approve_"))
async def approve_user(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    conn = sqlite3.connect("student_network.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (target_id,))
    conn.commit()
    conn.close()

    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\nTASDIQLANDI")
    await bot.send_message(target_id, "Anketangiz tasdiqlandi! Endi talabalarni ko'rishingiz mumkin.", reply_markup=main_menu())

@router.callback_query(F.data.startswith("reject_"))
async def reject_user(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    conn = sqlite3.connect("student_network.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (target_id,))
    conn.commit()
    conn.close()

    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\nRAD ETILDI")
    await bot.send_message(target_id, "Anketangiz rad etildi. Qayta ro'yxatdan o'tish uchun /start bosing.")

async def show_next_profile(message: Message, user_id: int):
    conn = sqlite3.connect("student_network.db")
    cursor = conn.cursor()
    cursor.execute("SELECT university, course, purpose, interests, age, target_gender, gender FROM users WHERE user_id = ?", (user_id,))
    me = cursor.fetchone()
    if not me:
        conn.close()
        return

    my_target = me[5]
    gender_filter = "Yigit" if my_target == "Yigitlar" else "Qiz" if my_target == "Qizlar" else None

    if gender_filter:
        query = "SELECT user_id, full_name, age, university, course, purpose, interests, bio, photo_id FROM users WHERE gender = ? AND user_id != ? AND is_verified = 1 AND user_id NOT IN (SELECT to_user_id FROM matches WHERE from_user_id = ?) LIMIT 1"
        cursor.execute(query, (gender_filter, user_id, user_id))
    else:
        query = "SELECT user_id, full_name, age, university, course, purpose, interests, bio, photo_id FROM users WHERE user_id != ? AND is_verified = 1 AND user_id NOT IN (SELECT to_user_id FROM matches WHERE from_user_id = ?) LIMIT 1"
        cursor.execute(query, (user_id, user_id))

    profile = cursor.fetchone()
    conn.close()

    if profile:
        target_id, name, age, uni, course, purpose, ints_json, bio, photo_id = profile
        interests = json.loads(ints_json) if ints_json else []
        ints_str = " • ".join(interests)

        caption = f"{name}, {age}\n{uni} ({course})\nMaqsad: {purpose}\n{ints_str}\n\nBio: {bio}"
        await message.answer_photo(photo=photo_id, caption=caption, reply_markup=action_keyboard(target_id))
    else:
        await message.answer("Hozircha yangi mos anketalar topilmadi. Birozdan so'ng qayta urinib ko'ring!")

@router.message(F.text == "Talabalarni ko'rish")
async def view_profiles(message: Message):
    await show_next_profile(message, message.from_user.id)

@router.callback_query(F.data.startswith("like_"))
async def process_like(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    from_id = callback.from_user.id

    conn = sqlite3.connect("student_network.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO matches (from_user_id, to_user_id, action) VALUES (?, ?, 'like')", (from_id, target_id))
    conn.commit()

    cursor.execute("SELECT action FROM matches WHERE from_user_id = ? AND to_user_id = ?", (target_id, from_id))
    match = cursor.fetchone()

    if match and match[0] == 'like':
        cursor.execute("INSERT OR REPLACE INTO active_chats (user_id, partner_id) VALUES (?, ?)", (from_id, target_id))
        cursor.execute("INSERT OR REPLACE INTO active_chats (user_id, partner_id) VALUES (?, ?)", (target_id, from_id))
        conn.commit()

        match_msg = "O'zaro Match bo'ldi! Endi anonim suhbat qilishingiz mumkin.\n\nSuhbatni boshlash uchun shunchaki xabar yozing:"
        await bot.send_message(from_id, match_msg, reply_markup=chat_keyboard())
        await bot.send_message(target_id, match_msg, reply_markup=chat_keyboard())

    conn.close()
    await callback.message.delete()
    await show_next_profile(callback.message, from_id)

@router.callback_query(F.data.startswith("pass_"))
async def process_pass(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    from_id = callback.from_user.id

    conn = sqlite3.connect("student_network.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO matches (from_user_id, to_user_id, action) VALUES (?, ?, 'pass')", (from_id, target_id))
    conn.commit()
    conn.close()

    await callback.message.delete()
    await show_next_profile(callback.message, from_id)

@router.message(F.text == "Muloqotni yakunlash")
async def stop_chat(message: Message):
    conn = sqlite3.connect("student_network.db")
    cursor = conn.cursor()
    cursor.execute("SELECT partner_id FROM active_chats WHERE user_id = ?", (message.from_user.id,))
    row = cursor.fetchone()

    if row:
        partner_id = row[0]
        cursor.execute("DELETE FROM active_chats WHERE user_id IN (?, ?)", (message.from_user.id, partner_id))
        conn.commit()

        await message.answer("Suhbat yakunlandi.", reply_markup=main_menu())
        await bot.send_message(partner_id, "Suhbatdoshingiz muloqotni yakunladi.", reply_markup=main_menu())
    else:
        await message.answer("Siz faol suhbatda emassiz.", reply_markup=main_menu())
    conn.close()

@router.message(F.text)
async def relay_chat_message(message: Message):
    conn = sqlite3.connect("student_network.db")
    cursor = conn.cursor()
    cursor.execute("SELECT partner_id FROM active_chats WHERE user_id = ?", (message.from_user.id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        partner_id = row[0]
        await bot.send_message(partner_id, f"Suhbatdosh: {message.text}")
    else:
        if message.text == "Profilim":
            await show_my_profile(message)

async def show_my_profile(message: Message):
    conn = sqlite3.connect("student_network.db")
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, age, university, course, purpose, interests, bio, photo_id FROM users WHERE user_id = ?", (message.from_user.id,))
    u = cursor.fetchone()
    conn.close()

    if u:
        ints = json.loads(u[5]) if u[5] else []
        caption = f"Anketangiz: {u[0]}, {u[1]}\n{u[2]} ({u[3]})\nMaqsad: {u[4]}\nQiziqishlar: {' • '.join(ints)}\n\nBio: {u[6]}"
        await message.answer_photo(photo=u[7], caption=caption)

async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
