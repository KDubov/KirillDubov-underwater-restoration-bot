import logging
import os
import asyncio
import json
import uuid
import shutil
import gspread

from aiogram import Bot, Dispatcher, types, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web
from gradio_client import Client, handle_file
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Конфигурация из переменных окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SPACE_URL = "https://kirilldubov-underwater-restoration.hf.space"
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID") 

# Инициализация
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Client(SPACE_URL)

# Настройка Google Sheets
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gs_client = gspread.authorize(creds)
sheet = gs_client.open_by_key("1OUxcrDV2cvheOqv__7Y9h_soHuqt7zsf3k91Qg38c5E").sheet1

def log_to_sheet(user_id, username, filename):
    try:
        sheet.append_row([str(datetime.now()), str(user_id), str(username), str(filename)])
    except Exception as e:
        logging.error(f"Ошибка записи в таблицу: {e}")

async def handle_root(request):
    return web.Response(text="Bot is running!")

async def process_image(message: types.Message, file_id: str, original_filename: str):
    user = message.from_user
    log_to_sheet(user.id, user.full_name, original_filename)
    
    status_msg = await message.answer("⏳ Обрабатываю... ~30–60 сек")
    
    unique_id = uuid.uuid4().hex
    local_input = f"input_{unique_id}.jpg"
    local_output = f"output_{unique_id}.jpg"
    
    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, local_input)
        result_path = client.predict(handle_file(local_input), 512, api_name="/enhance")
        shutil.copy(result_path, local_output)
        
        final_name = f"enhanced_{original_filename}"
        await message.answer_document(
            types.FSInputFile(local_output, filename=final_name),
            caption="✅ Готово!"
        )
        await bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
        
    except Exception as e:
        logging.error(f"Ошибка обработки: {e}")
        if ADMIN_CHAT_ID:
            await bot.send_message(
                ADMIN_CHAT_ID, 
                f"⚠️ **Ошибка у пользователя {user.full_name} (@{user.username}):**\n{str(e)}"
            )
        await message.answer("❌ Произошла ошибка при обработке фото. Попробуй позже.")
    finally:
        for f in [local_input, local_output]:
            if os.path.exists(f): os.remove(f)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Пришли фото.\n\n"
        "⚠️ Чтобы сохранить полное разрешение — отправляй как *файл* "
        "(📎скрепка → 📄Файл), а не как обычное фото.\n\n"
        "❗ Если не после отправки фото не появилось сообщение: \"⏳ Обрабатываю...\", — значит бот 💤 заснул.\n"
        "Подождите 5 минут ⏱ и отправьте снова, бот к этому времени проснется и даже выпьет кофе ☕",
        parse_mode="Markdown"
    )

@dp.message(Command("getid"))
async def get_id(message: types.Message):
    await message.answer(f"ID этого чата: {message.chat.id}")

@dp.message(Command("clear"))
async def cmd_clear(message: types.Message):
    current_id = message.message_id
    chat_id = message.chat.id
    
    # Сначала удалим само сообщение с командой /clear
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    # Собираем пачки по 100 ID (максимум для метода deleteMessages)
    # Пройдемся, например, на 150 сообщений назад двумя пачками
    for chunk in [range(1, 100), range(100, 151)]:
        message_ids_to_delete = []
        
        for i in chunk:
            # Вычисляем потенциальные ID предыдущих сообщений
            message_ids_to_delete.append(current_id - i)
        
        # Удаляем всю пачку одним запросом
        try:
            await bot.delete_messages(chat_id=chat_id, message_ids=message_ids_to_delete)
        except TelegramBadRequest:
            # Если в пачке есть старые (>48ч) или несуществующие сообщения,
            # Telegram Bot API может ругнуться, поэтому на случай сбоя пачки 
            # удалим их поштучно с пропуском ошибок
            for msg_id in message_ids_to_delete:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except TelegramBadRequest:
                    continue

class FeedbackStates(StatesGroup):
    waiting_for_feedback_text = State()

# 1. Хэндлер на саму команду /feedback
@dp.message(Command("feedback"))
async def cmd_feedback(message: types.Message, state: FSMContext):
    await message.answer("📝 Напишите ваше сообщение или отзыв разработчику:")
    # Переводим пользователя в состояние ожидания текста
    await state.set_state(FeedbackStates.waiting_for_feedback_text)

# 2. Хэндлер, который поймает СЛЕДУЮЩЕЕ сообщение пользователя
@dp.message(FeedbackStates.waiting_for_feedback_text)
async def process_feedback_text(message: types.Message, state: FSMContext):
    # ADMIN_CHAT_ID должен быть определен в ваших переменных окружения
    admin_chat_id = os.getenv("ADMIN_CHAT_ID") 
    
    if not admin_chat_id:
        await message.answer("❌ Ошибка: чат поддержки не настроен. Попробуйте позже.")
        await state.clear() # Сбрасываем состояние в случае ошибки
        return

    # Формируем красивый текст для группы админа
    feedback_delivery_text = (
        f"📩 **Новый отзыв!**\n"
        f"👤 От: {message.from_user.full_name} (@{message.from_user.username or 'нет_юзернейма'})\n"
        f"🆔 ID: `{message.from_user.id}`\n"
        f"---------------------\n"
        f"{message.text}"
    )

    try:
        # Отправляем сообщение в вашу группу обратной связи
        await bot.send_message(chat_id=admin_chat_id, text=feedback_delivery_text, parse_mode="Markdown")
        # Отвечаем пользователю
        await message.answer("✅ Сообщение отправлено. Благодарим вас за обратную связь!")
    except Exception as e:
        await message.answer("❌ Не удалось отправить сообщение. Попробуйте позже.")
        print(f"Ошибка отправки фидбека: {e}")
    
    # КРИТИЧЕСКИ ВАЖНО: сбрасываем состояние, чтобы бот снова реагировал на обычные команды и фото
    await state.clear()

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    try:
        count = len(sheet.get_all_values()) - 1 
        await message.answer(f"📊 Всего обработано фото: {count}")
    except Exception as e:
        await message.answer("Не удалось получить статистику.")

@dp.message(F.media_group_id)
async def handle_media_group(message: types.Message):
    await message.answer("⚠️ Пожалуйста, присылай фотографии **по одной**.", parse_mode="Markdown")
    
@dp.message(F.document)
async def handle_document(message: types.Message):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_name = message.document.file_name or "photo.jpg"
    name, ext = os.path.splitext(original_name)
    unique_filename = f"{name}_{timestamp}{ext}"
    await process_image(message, message.document.file_id, unique_filename)

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    photo = message.photo[-1]
    await process_image(message, photo.file_id, f"photo_{timestamp}.jpg")

async def on_startup(bot: Bot):
    await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)

async def main():
    app = web.Application()
    app.router.add_get("/", handle_root)
    setup_application(app, dp, bot=bot)
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    dp.startup.register(on_startup)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
