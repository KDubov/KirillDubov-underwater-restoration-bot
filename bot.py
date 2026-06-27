import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from gradio_client import Client, handle_file

BOT_TOKEN = "8988124989:AAHVEiW7G1y4kQBBRSSyWexTFbGJqrBLU1w"
SPACE_URL = "https://kirilldubov-underwater-restoration.hf.space"
# URL, который Render дает автоматически
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL") 
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Client(SPACE_URL)

# ... (функции cmd_start, process_image, handle_document, handle_photo оставь как были) ...

async def on_startup(bot: Bot):
    # При старте говорим Telegram, куда слать сообщения
    await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)

async def main():
    dp.startup.register(on_startup)
    
    app = web.Application()
    
    # Регистрация обработчика вебхуков
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    # Настройка приложения
    setup_application(app, dp, bot=bot)
    
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    logging.info(f"Starting server on port {port}")
    await site.start()
    
    # Вечный цикл, чтобы бот не выключался
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
