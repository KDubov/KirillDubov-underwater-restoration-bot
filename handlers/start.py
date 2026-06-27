from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def start(message: Message):

    await message.answer(
        "🌊 <b>Добро пожаловать в SeaClear AI!</b>\n\n"
        "Пришлите подводную фотографию, и я автоматически восстановлю её цвета."
    )
