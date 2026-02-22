# run.py — запускает бот + FastAPI бэкенд одновременно
import asyncio
import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from main import app  # импортируем FastAPI app из main.py

BOT_TOKEN = "8263129893:AAGKbAR_cjWyxTXnTLsxXX2KcH9f1aPQLiI"
WEBAPP_URL = "https://playful-bombolone-236702.netlify.app/"

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()

@dp.message(CommandStart())
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🔐 Открыть SPECTER VPN",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ]])
    await message.answer(
        "👋 Добро пожаловать в <b>SPECTER VPN</b>\n\n"
        "⚡ Ультра скорость · Zero Logs · Безопасный LTE\n\n"
        "Нажми кнопку ниже чтобы открыть приложение:",
        parse_mode="HTML",
        reply_markup=kb
    )

async def run_bot():
    print("🤖 Бот запущен...")
    await dp.start_polling(bot)

async def run_api():
    print("🚀 API запущен на порту 8000...")
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    await asyncio.gather(run_bot(), run_api())

if __name__ == "__main__":
    asyncio.run(main())
