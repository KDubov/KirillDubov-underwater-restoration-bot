from aiogram import F
from aiogram.types import Message, FSInputFile
import os
import uuid
from PIL import Image, ImageEnhance

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)


def setup_handlers(dp, bot, logger):

    @dp.message(F.text == "/start")
    async def start(message: Message):
        await message.answer("Бот запущен ✔ Отправь фото для обработки.")

    @dp.message(F.photo)
    async def handle_photo(message: Message):
        try:
            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)

            filename = f"{uuid.uuid4()}.jpg"
            path = os.path.join(TEMP_DIR, filename)

            await bot.download_file(file.file_path, destination=path)

            # простая обработка
            img = Image.open(path).convert("RGB")
            img = ImageEnhance.Contrast(img).enhance(1.3)
            img = ImageEnhance.Color(img).enhance(1.4)

            out_path = path.replace(".jpg", "_out.jpg")
            img.save(out_path)

            await message.answer_photo(FSInputFile(out_path))

        except Exception as e:
            logger.error(f"Photo error: {e}")
            await message.answer("Ошибка обработки фото ❌")
