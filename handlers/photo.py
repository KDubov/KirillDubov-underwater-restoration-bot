import uuid
from aiogram import F
from aiogram.types import Message
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

            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)

            path = f"/tmp/{uuid.uuid4()}.jpg"
            await bot.download_file(file.file_path, destination=path)

            # 🔥 ВАЖНО: твой Space + правильный endpoint
            client = Client(HF_SPACE)

            result = client.predict(
                handle_file(path),
                api_name="/enhance"   # 👈 ВОТ ЭТО ГЛАВНОЕ ИЗМЕНЕНИЕ
            )

            await message.answer("Готово ✔ отправляю результат...")

            # result = путь к файлу
            await message.answer_photo(result)

        except Exception as e:
            await message.answer(f"Ошибка: {e}")
            logger.error(e)
