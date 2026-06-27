import uuid
from aiogram import F
from aiogram.types import Message
from gradio_client import Client, handle_file

from config import HF_SPACE


def setup_handlers(dp, bot, logger):

    @dp.message(F.text == "/start")
    async def start(message: Message):
        await message.answer("Работаю ✔ отправь фото")

    @dp.message(F.photo)
    async def photo(message: Message):
        try:
            await message.answer("Получил фото, обрабатываю...")

            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)

            path = f"/tmp/{uuid.uuid4()}.jpg"
            await bot.download_file(file.file_path, destination=path)

            client = Client(HF_SPACE)

            await message.answer("Отправляю в HuggingFace...")

            result = client.predict(
                handle_file(path),
                api_name="/predict"
            )

            await message.answer(f"HF RESULT: {result}")

        except Exception as e:
            await message.answer(f"ERROR: {e}")
            logger.error(e)
