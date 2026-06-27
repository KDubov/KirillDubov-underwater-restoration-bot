import logging
import os
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiohttp import web
from gradio_client import Client, handle_file

BOT_TOKEN = "8988124989:AAH7OYAeyPXW_F0LH0Y-f2L1kFMZdtRcduA"
SPACE_URL = "https://kirilldubov-underwater-restoration.hf.space"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Client(SPACE_URL)

async def handle(request):
    return web.Response(text="Bot is running!")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Пришли подводное фото.\n\n"
        "⚠️ Чтобы сохранить полное разрешение — отправляй как *файл* "
        "(скрепка → Файл), а не как обычное фото.",
        parse_mode="Markdown"
    )

async def process_image(message: types.Message, file_id: str, filename: str):
    await message.answer("⏳ Обрабатываю... ~30–60 сек.")

    local_input = f"input_{file_id}.jpg"
    local_output = f"output_{file_id}.jpg"

    try:
        # Скачиваем входной файл
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, local_input)

        # Отправляем на HF Space и получаем путь к результату
        result_path = client.predict(
            handle_file(local_input),
            512,
            api_name="/enhance"
        )

        # result_path — локальный путь к файлу, скачанному gradio_client
        # gradio_client сам скачивает файл во временную папку
        import shutil
        shutil.copy(result_path, local_output)

        await message.answer_document(
            types.FSInputFile(local_output, filename="enhanced.jpg"),
            caption="✅ Готово! Файл в оригинальном разрешении."
        )

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer(f"❌ Ошибка: {e}")

    finally:
        for f in [local_input, local_output]:
            if os.path.exists(f):
                os.remove(f)

@dp.message(F.document)
async def handle_document(message: types.Message):
    """Документ — полное разрешение, рекомендуемый способ."""
    doc = message.document
    if not doc.mime_type or not doc.mime_type.startswith("image/"):
        return await message.answer("Пришли изображение как файл.")
    await process_image(message, doc.file_id, doc.file_name or "photo.jpg")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    """Фото — Telegram сжимает до 2560px, предупреждаем."""
    await message.answer(
        "📷 Получил фото, но Telegram сжал его до 2560px.\n"
        "Для полного разрешения отправь как *файл* (скрепка → Файл).\n\n"
        "Продолжаю обработку сжатой версии...",
        parse_mode="Markdown"
    )
    photo = message.photo[-1]
    await process_image(message, photo.file_id, "photo.jpg")

async def main():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
