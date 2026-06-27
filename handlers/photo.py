import uuid
import os
from aiogram import F
from aiogram.types import Message, FSInputFile
from gradio_client import Client, handle_file

from config import HF_SPACE


def setup_handlers(dp, bot, logger):

    @dp.message(F.text == "/start")
    async def start(message: Message):
        await message.answer("Отправь фото")

    @dp.message(F.photo)
    async def photo(message: Message):
        try:
            await message.answer("Обрабатываю фото...")

            # --- получаем фото ---
            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)

            # --- сохраняем локально ---
            path = f"/tmp/{uuid.uuid4()}.jpg"
            await bot.download_file(file.file_path, destination=path)

            # --- подключаем HF Space ---
            client = Client(HF_SPACE)

            result = client.predict(
                handle_file(path),
                api_name="/enhance"
            )

            await message.answer("Готово ✔ отправляю результат...")

            # --- обработка разных форматов ответа ---
            if isinstance(result, (tuple, list)):
                result = result[0]

            if not result:
                await message.answer("Ошибка: пустой результат от модели")
                return

            # --- отправка файла (ВАЖНО) ---
            if os.path.exists(result):
                await message.answer_photo(FSInputFile(result))
            else:
                await message.answer(f"Ошибка: файл не найден\n{result}")

        except Exception as e:
            logger.error(e)
            await message.answer(f"Ошибка: {e}")
