import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web
from gradio_client import Client, handle_file

# Конфигурация
BOT_TOKEN = "8988124989:AAH7OYAeyPXW_F0LH0Y-f2L1kFMZdtRcduA"
SPACE_URL = "https://kirilldubov-underwater-restoration.hf.space"

# Инициализация
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Client(SPACE_URL)

async def handle(request):
    return web.Response(text="Bot is running!")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Пришли мне подводное фото, и я его улучшу.")

@dp.message()
async def handle_photo(message: types.Message):
    if not message.photo:
        return await message.answer("Пожалуйста, пришли фото.")
    
    await message.answer("Обрабатываю... подожди немного.")
    
    # Скачиваем фото с максимальным разрешением
    file_id = message.photo[-1].file_id
    file = await bot.get_file(file_id)
    local_filename = f"input_{file_id}.jpg" # Уникальное имя для каждого фото
    await bot.download_file(file.file_path, local_filename)
    
    try:
        # Отправляем путь к файлу через handle_file
        # Gradio вернет путь к обработанному файлу
        result_path = client.predict(
            handle_file(local_filename), 
            512, 
            api_name="/enhance"
        )
        
        # Отправляем документ для сохранения оригинального качества
        await message.answer_document(types.FSInputFile(result_path))
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer(f"Ошибка при обработке: {e}")
    finally:
        # Удаляем локальный файл, чтобы не засорять диск
        if os.path.exists(local_filename):
            os.remove(local_filename)

async def main():
    # Запуск веб-сервера
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
