import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from handlers.photo import setup_handlers
from handlers.start import setup_start

from config import BOT_TOKEN
from photo import setup_handlers


WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Render URL


async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL + WEBHOOK_PATH)
    print("Webhook set:", WEBHOOK_URL + WEBHOOK_PATH)


async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    print("Webhook deleted")


def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    setup_handlers(dp, bot, logging.getLogger(__name__))

    app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    app.on_startup.append(lambda app: on_startup(bot))
    app.on_shutdown.append(lambda app: on_shutdown(bot))

    return app


if __name__ == "__main__":
    app = main()
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
