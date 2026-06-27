import uuid
import os
from aiogram import F
from aiogram.types import Message, FSInputFile
from gradio_client import Client
from PIL import Image

from config import HF_SPACE


def setup_handlers(dp, bot, logger):

    @dp.message(F.text == "/start")
    async def start(message: Message):
        await message.answer(
            "Отправь изображение как ФАЙЛ (📎 без сжатия), чтобы сохранить исходное качество."
        )

    @dp.message(F.photo)
    async def photo_compressed(message: Message):
        await message.answer(
            "⚠️ Ты отправил фото (Telegram сжал его).\n"
            "Для максимального качества отправь как ФАЙЛ 📎"
        )

    @dp.message(F.document)
    async def photo(message: Message):
        try:
            # --- проверка ---
            if not message.document.mime_type.startswith("image/"):
                await message.answer("Отправь изображение как файл 📎")
                return

            await message.answer("Обрабатываю фото...")

            # --- скачивание оригинального файла ---
            file = await bot.get_file(message.document.file_id)

            path = f"/tmp/{uuid.uuid4()}.jpg"
            await bot.download_file(file.file_path, destination=path)

            if not os.path.exists(path):
                await message.answer("Ошибка: файл не сохранён локально")
                return

            # --- PIL IMAGE MODE (ВАЖНО) ---
            image = Image.open(path).convert("RGB")

            # --- HF Space ---
            client = Client(HF_SPACE)

            result = client.predict(
                image,
                api_name="/enhance"
            )

            await message.answer("Готово ✔ отправляю результат...")

            # --- нормализация результата ---
            if isinstance(result, (tuple, list)):
                result = result[0]

            if isinstance(result, dict):
                result = result.get("path") or result.get("image")

            if not result:
                await message.answer(f"Ошибка: пустой результат\n{result}")
                return

            if not os.path.exists(result):
                await message.answer(f"Ошибка: файл не найден\n{result}")
                return

            # --- отправка результата ---
            await message.answer_photo(FSInputFile(result))

        except Exception as e:
            logger.error(e)
            await message.answer(f"Ошибка: {e}")
