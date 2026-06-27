import logging
import os
import asyncio
import json
import uuid
import shutil
import gspread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from gradio_client import Client, handle_file
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Конфигурация из переменных окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SPACE_URL = "https://kirilldubov-underwater-restoration.hf.space"
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"

# Инициализация
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Client(SPACE_URL)

# Настройка Google Sheets
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gs_client = gspread.authorize(creds)
sheet = gs_client.open_by_key("1OUxcrDV2cvheOqv__7Y9h_soHuqt7zsf3k91Qg38c5E").sheet1

def log_to_sheet(user_id, username, filename):
    try:
        sheet.append_row([str(datetime.now()), str(user_id), str(username), str(filename)])
    except Exception as e:
        logging.error(f"Ошибка записи в таблицу: {e}")

async def handle_root(request):
    return web.Response(text="Bot is running!")

async def process_image(message: types.Message, file_id: str, original_filename: str):
    user = message.from_user
    log_to_sheet(user.id, user.full_name, original_filename)
    await message.answer("⏳ Processing...")
    
    unique_id = uuid.uuid4().hex
    local_input = f"input_{unique_id}.jpg"
    local_output = f"output_{unique_id}.jpg"
    
    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, local_input)
        result_path = client.predict(handle_file(local_input), 512, api_name="/enhance")
        shutil.copy(result_path, local_output)
        await message.answer_document(types.FSInputFile(local_output, filename="enhanced.jpg"))
    finally:
        for f in [local_input, local_output]:
            if os.path.exists(f): os.remove(f)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hi! Send a photo as a FILE for full resolution.")

@dp.message(F.document)
async def handle_document(message: types.Message):
    await process_image(message, message.document.file_id, message.document.file_name or "photo.jpg")

async def on_startup(bot: Bot):
    await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)

async def main():
    app = web.Application()
    app.router.add_get("/", handle_root)
    setup_application(app, dp, bot=bot)
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    dp.startup.register(on_startup)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
