import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from gradio_client import Client
import asyncio

# Используем переменные окружения для безопасности
# (Ты их укажешь позже в настройках Render)
BOT_TOKEN = os.getenv("8988124989:AAH7OYAeyPXW_F0LH0Y-f2L1kFMZdtRcduA")
SPACE_URL = "https://huggingface.co/spaces/KirillDubov/underwater-restoration" 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Подключаемся к твоему Space
client = Client(SPACE_URL)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Пришли мне подводное фото, и я его улучшу.")

@dp.message()
async def handle_photo(message: types.Message):
    if not message.photo:
        return await message.answer("Пожалуйста, пришли фото.")
    
    await message.answer("Обрабатываю... подожди немного.")
    
    # Берем фото самого высокого качества
    file_id = message.photo[-1].file_id
    file = await bot.get_file(file_id)
    
    # Скачиваем файл временно
    local_filename = "input.jpg"
    await bot.download_file(file.file_path, local_filename)
    
    # Отправляем в твой Space (api_name="/predict" — это стандарт для Gradio)
    try:
        result = client.predict(local_filename, api_name="/predict")
        # result - это путь к обработанному файлу
        await message.answer_document(types.FSInputFile(result))
    except Exception as e:
        await message.answer(f"Ошибка при обработке: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
