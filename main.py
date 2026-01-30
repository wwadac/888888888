"""
СТИКЕР-БОТ ДЛЯ TELEGRAM
Функция: когда ты пишешь человеку "привет", бот отправляет от твоего лица стикер
Автор: t.me/fuck_zaza
"""

import os
import json
import asyncio
import logging
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

# Файл для хранения данных
DATA_FILE = 'sticker_bot_data.json'

# Инициализация бота для aiogram 3.7+
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher(storage=MemoryStorage())

# Состояния FSM
class StickerStates(StatesGroup):
    waiting_for_sticker = State()

# Фразы-триггеры
TRIGGER_PHRASES = [
    'привет', 'прив', 'хай', 'хей', 'hello', 'hi', 'hey',
    'здравствуй', 'здравствуйте', 'добрый день', 'доброе утро',
    'добрый вечер', 'салют', 'ку', 'здарова', 'приветствую',
    'приветик', 'здорово'
]

# Загрузка данных
def load_data():
    """Загружает сохраненные данные"""
    default_data = {
        'sticker_id': None,
        'owner_id': ADMIN_ID,
        'last_used': None,
        'total_sent': 0
    }
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
    
    return default_data

# Сохранение данных
def save_data(data):
    """Сохраняет данные"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")
        return False

# Проверка триггерной фразы
def is_trigger_message(text):
    """Проверяет, содержит ли сообщение триггерную фразу"""
    if not text:
        return False
    
    text_lower = text.strip().lower()
    
    # Простая проверка по списку
    for phrase in TRIGGER_PHRASES:
        if phrase == text_lower:
            return True
        if phrase in text_lower and len(text_lower) < 50:
            return True
    
    return False

# Отправка стикера
async def send_sticker_as_user(chat_id, business_connection_id=None):
    """Отправляет стикер от имени пользователя"""
    data = load_data()
    sticker_id = data.get('sticker_id')
    
    if not sticker_id:
        logger.warning("ID стикера не установлен")
        return False
    
    try:
        if business_connection_id:
            # Отправка через бизнес-подключение
            await bot.send_sticker(
                chat_id=chat_id,
                sticker=sticker_id,
                business_connection_id=business_connection_id
            )
        else:
            # Обычная отправка
            await bot.send_sticker(
                chat_id=chat_id,
                sticker=sticker_id
            )
        
        # Обновляем статистику
        data['last_used'] = datetime.now().isoformat()
        data['total_sent'] = data.get('total_sent', 0) + 1
        save_data(data)
        
        logger.info(f"Стикер отправлен в чат {chat_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки стикера: {e}")
        return False

# ==================== КОМАНДЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда /start"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Этот бот доступен только владельцу")
        return
    
    data = load_data()
    sticker_status = "✅ Установлен" if data.get('sticker_id') else "❌ Не установлен"
    total_sent = data.get('total_sent', 0)
    last_used = data.get('last_used', 'никогда')
    
    await message.answer(
        f"👋 <b>Стикер-бот запущен</b>\n\n"
        f"📊 <b>Статус:</b> {sticker_status}\n"
        f"📨 <b>Отправлено стикеров:</b> {total_sent}\n"
        f"⏰ <b>Последняя отправка:</b> {last_used}\n\n"
        f"<b>Как использовать:</b>\n"
        f"1. Отправь мне стикер командой /setsticker\n"
        f"2. Пиши людям 'привет' в личных сообщениях\n"
        f"3. Бот автоматически отправит твой стикер\n\n"
        f"<b>Триггерные фразы:</b>\n"
        f"{', '.join(TRIGGER_PHRASES[:10])}"
    )

@dp.message(Command("setsticker"))
async def cmd_set_sticker(message: types.Message, state: FSMContext):
    """Команда для установки стикера"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен")
        return
    
    await state.set_state(StickerStates.waiting_for_sticker)
    await message.answer(
        "📎 <b>Отправь мне стикер, который я буду использовать</b>\n\n"
        "Просто отправь любой стикер в этот чат, и я сохраню его ID\n"
        "После этого буду отправлять его от твоего лица когда ты пишешь 'привет'"
    )

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Статистика бота"""
    if message.from_user.id != ADMIN_ID:
        return
    
    data = load_data()
    sticker_id = data.get('sticker_id', 'не установлен')
    
    if sticker_id != 'не установлен':
        try:
            # Показываем превью стикера
            await message.answer_sticker(sticker_id)
        except:
            pass
    
    await message.answer(
        f"📊 <b>Статистика бота</b>\n\n"
        f"🆔 <b>ID стикера:</b>\n<code>{sticker_id[:50]}...</code>\n"
        f"📨 <b>Всего отправлено:</b> {data.get('total_sent', 0)}\n"
        f"⏰ <b>Последняя отправка:</b> {data.get('last_used', 'никогда')}\n"
        f"👤 <b>Владелец:</b> {ADMIN_ID}\n\n"
        f"<b>Триггерные фразы:</b>\n"
        f"{', '.join(TRIGGER_PHRASES[:8])}..."
    )

@dp.message(Command("test"))
async def cmd_test(message: types.Message):
    """Тестовая отправка стикера"""
    if message.from_user.id != ADMIN_ID:
        return
    
    data = load_data()
    if not data.get('sticker_id'):
        await message.answer("❌ Стикер не установлен. Используй /setsticker")
        return
    
    try:
        await message.answer("🔄 Тестовая отправка стикера...")
        await send_sticker_as_user(message.chat.id)
        await message.answer("✅ Стикер отправлен успешно!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

# ==================== ОБРАБОТКА СТИКЕРОВ ====================

@dp.message(StickerStates.waiting_for_sticker, F.sticker)
async def process_sticker_input(message: types.Message, state: FSMContext):
    """Обработка полученного стикера"""
    if message.from_user.id != ADMIN_ID:
        return
    
    sticker = message.sticker
    sticker_id = sticker.file_id
    
    # Сохраняем данные
    data = load_data()
    data['sticker_id'] = sticker_id
    data['set_by'] = message.from_user.id
    data['set_at'] = datetime.now().isoformat()
    save_data(data)
    
    await state.clear()
    
    # Показываем стикер для подтверждения
    await message.answer_sticker(sticker_id)
    await message.answer(
        f"✅ <b>Стикер сохранен!</b>\n\n"
        f"<b>ID:</b> <code>{sticker_id[:50]}...</code>\n"
        f"<b>Emoji:</b> {sticker.emoji or 'нет'}\n"
        f"<b>Набор:</b> {sticker.set_name or 'нет'}\n\n"
        f"Теперь когда ты пишешь 'привет' в личных сообщениях,\n"
        f"я буду отправлять этот стикер от твоего лица!"
    )

# ==================== ОСНОВНАЯ ЛОГИКА ====================

@dp.message(F.text)
async def handle_private_message(message: types.Message):
    """
    Обрабатывает ВСЕ текстовые сообщения, которые ты отправляешь
    Проверяет, пишешь ли ты 'привет' кому-то
    """
    try:
        # Только сообщения ОТ владельца (тебя)
        if message.from_user.id != ADMIN_ID:
            return
        
        # Только личные сообщения (не группы/каналы)
        if message.chat.type not in ['private', 'sender']:
            return
        
        # Получаем текст сообщения
        text = message.text.strip()
        if not text:
            return
        
        # Проверяем на триггерные фразы
        if is_trigger_message(text):
            logger.info(f"Триггер сработал: '{text}' в чате {message.chat.id}")
            
            # Задержка перед отправкой (имитация человека)
            delay = random.uniform(0.5, 2.0)
            await asyncio.sleep(delay)
            
            # Отправляем стикер
            await send_sticker_as_user(message.chat.id)
            
            logger.info(f"Стикер отправлен в ответ на '{text}'")
    
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")

@dp.message(F.sticker)
async def handle_sticker_message(message: types.Message):
    """Обработка стикеров (кроме состояния установки)"""
    if message.from_user.id != ADMIN_ID:
        return
    
    data = load_data()
    if data.get('sticker_id'):
        # Если стикер уже установлен, просто показываем инфу
        await message.answer(
            f"📎 У тебя уже установлен стикер\n"
            f"Используй /setsticker для изменения"
        )

# ==================== BUSINESS API ПОДДЕРЖКА ====================

@dp.business_message(F.text)
async def handle_business_text(message: types.Message):
    """
    Обработка сообщений через Business API
    Когда ты пишешь 'привет' через бизнес-аккаунт
    """
    try:
        if not hasattr(message, 'business_connection_id'):
            return
        
        # Только сообщения ОТ владельца
        if message.from_user.id != ADMIN_ID:
            return
        
        # Проверяем текст
        text = message.text.strip()
        if not text:
            return
        
        # Проверяем триггерные фразы
        if is_trigger_message(text):
            logger.info(f"Бизнес-триггер: '{text}' в чате {message.chat.id}")
            
            # Задержка
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # Отправляем стикер через бизнес-подключение
            data = load_data()
            sticker_id = data.get('sticker_id')
            
            if sticker_id:
                await bot.send_sticker(
                    chat_id=message.chat.id,
                    sticker=sticker_id,
                    business_connection_id=message.business_connection_id
                )
                
                # Обновляем статистику
                data['total_sent'] = data.get('total_sent', 0) + 1
                data['last_used'] = datetime.now().isoformat()
                save_data(data)
                
                logger.info(f"Бизнес-стикер отправлен")
    
    except Exception as e:
        logger.error(f"Ошибка бизнес-обработки: {e}")

# ==================== ЗАПУСК БОТА ====================

async def main():
    """Запуск бота"""
    print("=" * 50)
    print("🤖 СТИКЕР-БОТ ДЛЯ TELEGRAM")
    print("Функция: автоматическая отправка стикера когда ты пишешь 'привет'")
    print(f"👤 Владелец: {ADMIN_ID}")
    print("=" * 50)
    
    # Проверяем данные
    data = load_data()
    if data.get('sticker_id'):
        print(f"✅ Стикер установлен (отправлено: {data.get('total_sent', 0)})")
    else:
        print("⚠️ Стикер не установлен. Используй /setsticker")
    
    print("🔄 Бот запущен и слушает сообщения...")
    print("📝 Триггерные фразы:", ", ".join(TRIGGER_PHRASES[:5]) + "...")
    print("=" * 50)
    
    # Устанавливаем команды
    await bot.set_my_commands([
        types.BotCommand(command="start", description="Запустить бота"),
        types.BotCommand(command="setsticker", description="Установить стикер"),
        types.BotCommand(command="stats", description="Статистика"),
        types.BotCommand(command="test", description="Тест стикера")
    ])
    
    # Запускаем polling
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
