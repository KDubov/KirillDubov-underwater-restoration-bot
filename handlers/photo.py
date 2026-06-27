import os
import uuid
from aiogram import F
from aiogram.types import Message, FSInputFile
from PIL import Image, ImageEnhance


# Папка для временных файлов
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)


def setup_handlers(dp, bot, logger):

    @dp.message(F.photo)
    async def handle_photo(message: Message):
        try:
            logger.info("Photo received")

            # 1. Скачать файл
            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)

            filename = f"{uuid.uuid4()}.jpg"
            path = os.path.join(TEMP_DIR, filename)

            await bot.download_file(file.file_path, destination=path)

            logger.info(f"Saved photo to {path}")

            # 2. Обработать фото
            processed_path = process_image(path)

            # 3. Отправить обратно
            await message.answer_photo(FSInputFile(processed_path))

            logger.info("Photo processed and sent back")

        except Exception as e:
            logger.error(f"Error processing photo: {e}")
            await message.answer("Ошибка при обработке фото 😢")


def process_image(path: str) -> str:
    """
    Простая заглушка цветокоррекции под водой
    (потом заменим на AI-модель)
    """

    img = Image.open(path).convert("RGB")

    # Лёгкая цветокоррекция (имитация "dehaze underwater")
    img = ImageEnhance.Contrast(img).enhance(1.3)
    img = ImageEnhance.Color(img).enhance(1.5)
    img = ImageEnhance.Brightness(img).enhance(1.1)

    out_path = path.replace(".jpg", "_out.jpg")
    img.save(out_path, quality=95)

    return out_path
