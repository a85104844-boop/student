import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# Logging
logging.basicConfig(level=logging.INFO)

# Telegram Bot Token
BOT_TOKEN = "7953282218:AAEP2wUjG0Kx2cWv2Zz7T3f_f5m58qZ0z58" # O'zingizning tokeningiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# /start komandasi
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Salom! Student Social Network botiga xush kelibsiz.")

# Render port talabi uchun soxta Web-server (Port ping)
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    # Web server va Polling'ni bir vaqtda ishga tushirish
    asyncio.create_task(start_web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
