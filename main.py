import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db
from handlers import router

async def main():
    # Инициализация БД
    await init_db()
    
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Подключение всех наших хэндлеров из handlers.py
    dp.include_router(router)
    
    print("🚀 Бот запущен! Ожидание сообщений...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())