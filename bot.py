import logging
import os
import asyncio
import aiohttp
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
        # 1. Получаем путь к файлу от Gradio
        result_path = client.predict(handle_file(local_filename), 512, api_name="/enhance")
        
        # 2. Скачиваем файл напрямую через aiohttp
        # Gradio возвращает путь, нам нужно получить к нему доступ. 
        # Если это локальный путь, мы можем его прочитать. 
        # Если удаленный — скачиваем через url.
        
        # В большинстве случаев на HuggingFace Space результат доступен по прямой ссылке:
        file_url = f"{SPACE_URL}/file={result_path}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    with open("final_result.jpg", "wb") as f:
                        f.write(data)
                    
                    # 3. Отправляем фото
                    await message.answer_document(types.FSInputFile("final_result.jpg"))
                else:
                    await message.answer("Ошибка скачивания файла с сервера.")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer(f"Ошибка при обработке: {e}")

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
