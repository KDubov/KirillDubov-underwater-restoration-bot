import logging
import os
import asyncio
import shutil
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from gradio_client import Client, handle_file

# Конфигурация
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не задана!")
SPACE_URL = "https://kirilldubov-underwater-restoration.hf.space"
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"

# Инициализация
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Client(SPACE_URL)

async def handle_root(request):
    return web.Response(text="Bot is running!")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Hi! Send the photo.\n\n"
        "⚠️ To preserve full resolution, send it as a *file*. "
        "(📎paperclip → 📄File), rather than as a regular photo.",
        parse_mode="Markdown"
    )

async def process_image(message: types.Message, file_id: str, original_filename: str):
    await message.answer("⏳ Processing... / Обрабатываю... ~30–60 sec.")
    
    # Генерируем уникальный ID для этой сессии, чтобы избежать конфликтов файлов
    unique_id = uuid.uuid4().hex
    local_input = f"input_{unique_id}.jpg"
    local_output = f"output_{unique_id}.jpg"
    
    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, local_input)
        
        result_path = client.predict(handle_file(local_input), 512, api_name="/enhance")
        shutil.copy(result_path, local_output)
        
        await message.answer_document(
            types.FSInputFile(local_output, filename=f"enhanced_{original_filename}"),
            caption="✅ Done / Готово!"
        )
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer(f"❌ Error / Ошибка: {e}")
    finally:
        # Удаляем временные файлы, созданные для этого пользователя[cite: 1]
        for f in [local_input, local_output]:
            if os.path.exists(f): os.remove(f)

@dp.message(F.document)
async def handle_document(message: types.Message):
    doc = message.document
    if not doc.mime_type or not doc.mime_type.startswith("image/"):
        return await message.answer("Пришли изображение как файл.")
    await process_image(message, doc.file_id, doc.file_name or "photo.jpg")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    await message.answer("📷 Получил фото, но Telegram сжал его. Для полного разрешения отправь как файл.", parse_mode="Markdown")
    photo = message.photo[-1]
    await process_image(message, photo.file_id, "photo.jpg")

async def on_startup(bot: Bot):
    await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)

async def main():
    app = web.Application()
    app.router.add_get("/", handle_root)
    
    setup_application(app, dp, bot=bot)
    
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    dp.startup.register(on_startup)
    
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    logging.info(f"Starting server on port {port}")
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
