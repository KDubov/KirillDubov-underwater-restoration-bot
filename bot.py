import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from gradio_client import Client
import asyncio
from aiohttp import web

# Твой токен (можно вписать сюда напрямую, если переменные окружения капризничают)
BOT_TOKEN = "8988124989:AAH7OYAeyPXW_F0LH0Y-f2L1kFMZdtRcduA"
# Адрес твоего Space
SPACE_URL = "https://kirilldubov-underwater-restoration.hf.space"

client = Client(SPACE_URL)
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Это "заглушка" для Render, чтобы он видел открытый порт
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
    
    file_id = message.photo[-1].file_id
    file = await bot.get_file(file_id)
    local_filename = "input.jpg"
    await bot.download_file(file.file_path, local_filename)
    
    try:
        # Отправляем фото в твой Space
        result = client.predict(local_filename, api_name="/enhance")
        await message.answer_document(types.FSInputFile(result))
    except Exception as e:
        await message.answer(f"Ошибка при обработке: {e}")

async def main():
    # 1. Запускаем веб-сервер (обязательно для Web Service на Render)
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render подставляет порт в переменную окружения PORT
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    # 2. Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
