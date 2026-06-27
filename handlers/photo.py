import os
import uuid
from aiogram import F
from aiogram.types import Message
from gradio_client import Client

from config import HF_SPACE


def setup_handlers(dp, bot, logger):

    @dp.message(F.text == "/start")
    async def start(message: Message):
        await message.answer("Отправь фото")

    @dp.message(F.photo)
    async def handle_photo(message: Message):
        try:
            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)

            path = f"/tmp/{uuid.uuid4()}.jpg"
            await bot.download_file(file.file_path, destination=path)

            # 🔥 HuggingFace Space client
            client = Client(HF_SPACE)

            # ⚠️ ВАЖНО: это стандартный /predict
            result = client.predict(path, api_name="/predict")

            # result обычно = путь к файлу
            if isinstance(result, str) and os.path.exists(result):
                await message.answer_photo(result)
            else:
                await message.answer(f"HF response: {result}")

        except Exception as e:
            logger.error(e)
            await message.answer("Ошибка обработки")
