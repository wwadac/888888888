

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
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
    waiting_for_reply_text = State()

# Фразы-триггеры для приветствия
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
        'reply_texts': [],  # Новый: список текстов для автоответов
        'owner_id': ADMIN_ID,
        'last_used': None,
        'total_sent': 0,
        'last_reply_time': {}  # Для кулдауна по чатам
    }
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Добавляем новые поля если их нет
                if 'reply_texts' not in data:
                    data['reply_texts'] = []
                if 'last_reply_time' not in data:
                    data['last_reply_time'] = {}
                return data
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

# Отправка автоответа с имитацией человека
async def send_auto_reply(chat_id, business_connection_id=None):
    """Отправляет случайный текст из списка с задержкой, имитацией чтения/печати и кулдауном"""
    data = load_data()
    reply_texts = data.get('reply_texts', [])
    
    if not reply_texts:
        logger.warning("Тексты автоответов не установлены")
        return False
    
    reply_text = random.choice(reply_texts)
    
    current_time = datetime.now()
    last_reply = data['last_reply_time'].get(str(chat_id))
    
    if last_reply:
        last_time = datetime.fromisoformat(last_reply)
        cooldown = random.randint(10, 30) + random.uniform(0, 5)  # 10-30 сек + рандом до 5 сек
        if (current_time - last_time).total_seconds() < cooldown:
            logger.info(f"Кулдаун активен для чата {chat_id}")
            return False
    
    try:
        # Имитация чтения сообщения (chat_action: typing на 2-5 сек)
        read_delay = random.uniform(2, 5)
        await bot.send_chat_action(
            chat_id=chat_id,
            action="typing",
            business_connection_id=business_connection_id
        )
        await asyncio.sleep(read_delay)
        
        # Имитация печати (еще typing на 3-7 сек)
        type_delay = random.uniform(3, 7)
        await bot.send_chat_action(
            chat_id=chat_id,
            action="typing",
            business_connection_id=business_connection_id
        )
        await asyncio.sleep(type_delay)
        
        # Отправка текста
        if business_connection_id:
            await bot.send_message(
                chat_id=chat_id,
                text=reply_text,
                business_connection_id=business_connection_id
            )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=reply_text
            )
        
        # Обновляем статистику и кулдаун
        data['last_used'] = current_time.isoformat()
        data['total_sent'] = data.get('total_sent', 0) + 1
        data['last_reply_time'][str(chat_id)] = current_time.isoformat()
        save_data(data)
        
        logger.info(f"Автоответ отправлен в чат {chat_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки автоответа: {e}")
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
    replies_count = len(data.get('reply_texts', []))
    replies_status = f"✅ {replies_count} шт." if replies_count > 0 else "❌ Не установлены"
    total_sent = data.get('total_sent', 0)
    last_used = data.get('last_used', 'никогда')
    
    # Inline кнопки для меню
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Установить стикер", callback_data="set_sticker")],
        [InlineKeyboardButton(text="Добавить автоответ", callback_data="add_reply_text")],
        [InlineKeyboardButton(text="Список автоответов", callback_data="list_replies")],
        [InlineKeyboardButton(text="Очистить автоответы", callback_data="clear_replies")],
        [InlineKeyboardButton(text="Статистика", callback_data="show_stats")],
        [InlineKeyboardButton(text="Тест", callback_data="test_bot")]
    ])
    
    await message.answer(
        f"👋 Стикер-бот запущен\n\n"
        f"📊 Статус стикера: {sticker_status}\n"
        f"📊 Автоответы: {replies_status}\n"
        f"📨 Отправлено всего: {total_sent}\n"
        f"⏰ Последняя отправка: {last_used}\n\n"
        f"Как использовать:\n"
        f"1. Установи стикер и добавь тексты автоответов\n"
        f"2. Пиши 'привет' - бот отправит стикер\n"
        f"3. Когда пользователь ответит - бот отправит случайный текст с задержкой\n\n"
        f"Триггерные фразы:\n"
        f"{', '.join(TRIGGER_PHRASES[:10])}",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "set_sticker")
async def cb_set_sticker(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await state.set_state(StickerStates.waiting_for_sticker)
    await callback.message.answer(
        "📎 Отправь мне стикер для установки"
    )
    await callback.answer()

@dp.callback_query(F.data == "add_reply_text")
async def cb_add_reply_text(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await state.set_state(StickerStates.waiting_for_reply_text)
    await callback.message.answer(
        "✍️ Отправь текст для добавления в автоответы\n\n"
        "Этот текст будет добавлен в список. Бот выберет случайный при отправке"
    )
    await callback.answer()

@dp.callback_query(F.data == "list_replies")
async def cb_list_replies(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    data = load_data()
    reply_texts = data.get('reply_texts', [])
    if not reply_texts:
        await callback.message.answer("❌ Нет автоответов")
    else:
        replies_list = "\n".join([f"{i+1}. {text[:50]}..." for i, text in enumerate(reply_texts)])
        await callback.message.answer(f"📝 Список автоответов:\n{replies_list}\n\nИспользуй /removereply <номер> для удаления")
    await callback.answer()

@dp.callback_query(F.data == "clear_replies")
async def cb_clear_replies(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    data = load_data()
    data['reply_texts'] = []
    save_data(data)
    await callback.message.answer("✅ Все автоответы очищены")
    await callback.answer()

@dp.callback_query(F.data == "show_stats")
async def cb_show_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    await cmd_stats(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "test_bot")
async def cb_test_bot(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    await cmd_test(callback.message)
    await callback.answer()

@dp.message(Command("setsticker"))
async def cmd_set_sticker(message: types.Message, state: FSMContext):
    """Команда для установки стикера"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен")
        return
    
    await state.set_state(StickerStates.waiting_for_sticker)
    await message.answer(
        "📎 Отправь мне стикер, который я буду использовать\n\n"
        "Просто отправь любой стикер в этот чат, и я сохраню его ID\n"
        "После этого буду отправлять его от твоего лица когда ты пишешь 'привет'"
    )

@dp.message(Command("addreplytext"))
async def cmd_add_reply_text(message: types.Message, state: FSMContext):
    """Команда для добавления текста автоответа"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен")
        return
    
    await state.set_state(StickerStates.waiting_for_reply_text)
    await message.answer(
        "✍️ Отправь текст для добавления в автоответы\n\n"
        "Этот текст будет добавлен в список. Бот выберет случайный при отправке\n"
        "С кулдауном 10-30 сек + рандом, имитацией печати и чтения"
    )

@dp.message(Command("listreplies"))
async def cmd_list_replies(message: types.Message):
    """Список автоответов"""
    if message.from_user.id != ADMIN_ID:
        return
    
    data = load_data()
    reply_texts = data.get('reply_texts', [])
    if not reply_texts:
        await message.answer("❌ Нет автоответов")
    else:
        replies_list = "\n".join([f"{i+1}. {text[:50]}..." for i, text in enumerate(reply_texts)])
        await message.answer(f"📝 Список автоответов:\n{replies_list}\n\nИспользуй /removereply <номер> для удаления")

@dp.message(Command("removereply"))
async def cmd_remove_reply(message: types.Message):
    """Удаление автоответа по номеру"""
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        index = int(message.text.split()[1]) - 1
        data = load_data()
        reply_texts = data.get('reply_texts', [])
        if 0 <= index < len(reply_texts):
            removed = reply_texts.pop(index)
            save_data(data)
            await message.answer(f"✅ Удален: {removed[:50]}...")
        else:
            await message.answer("❌ Неверный номер")
    except:
        await message.answer("❌ Использование: /removereply <номер>")

@dp.message(Command("clearreplies"))
async def cmd_clear_replies(message: types.Message):
    """Очистка всех автоответов"""
    if message.from_user.id != ADMIN_ID:
        return
    
    data = load_data()
    data['reply_texts'] = []
    save_data(data)
    await message.answer("✅ Все автоответы очищены")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Статистика бота"""
    if message.from_user.id != ADMIN_ID:
        return
    
    data = load_data()
    sticker_id = data.get('sticker_id', 'не установлен')
    reply_texts = data.get('reply_texts', [])
    replies_count = len(reply_texts)
    replies_preview = ", ".join([text[:20] + "..." for text in reply_texts[:3]]) if reply_texts else "нет"
    
    if sticker_id != 'не установлен':
        try:
            # Показываем превью стикера
            await message.answer_sticker(sticker_id)
        except:
            pass
    
    await message.answer(
        f"📊 Статистика бота\n\n"
        f"🆔 ID стикера:\n{sticker_id[:50]}...\n"
        f"📝 Автоответы: {replies_count} шт. ({replies_preview})\n"
        f"📨 Всего отправлено: {data.get('total_sent', 0)}\n"
        f"⏰ Последняя отправка: {data.get('last_used', 'никогда')}\n"
        f"👤 Владелец: {ADMIN_ID}\n\n"
        f"Триггерные фразы:\n"
        f"{', '.join(TRIGGER_PHRASES[:8])}..."
    )

@dp.message(Command("test"))
async def cmd_test(message: types.Message):
    """Тестовая отправка стикера и автоответа"""
    if message.from_user.id != ADMIN_ID:
        return
    
    data = load_data()
    if not data.get('sticker_id') and not data.get('reply_texts'):
        await message.answer("❌ Ничего не установлено. Используй /setsticker или /addreplytext")
        return
    
    try:
        await message.answer("🔄 Тестовая отправка...")
        if data.get('sticker_id'):
            await send_sticker_as_user(message.chat.id)
        if data.get('reply_texts'):
            await send_auto_reply(message.chat.id)
        await message.answer("✅ Тест выполнен успешно!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

# ==================== ОБРАБОТКА ВВОДА ====================

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
        f"✅ Стикер сохранен!\n\n"
        f"ID: {sticker_id[:50]}...\n"
        f"Emoji: {sticker.emoji or 'нет'}\n"
        f"Набор: {sticker.set_name or 'нет'}\n\n"
        f"Теперь когда ты пишешь 'привет' в личных сообщениях,\n"
        f"я буду отправлять этот стикер от твоего лица!"
    )

@dp.message(StickerStates.waiting_for_reply_text, F.text)
async def process_reply_text_input(message: types.Message, state: FSMContext):
    """Обработка полученного текста для автоответа"""
    if message.from_user.id != ADMIN_ID:
        return
    
    reply_text = message.text.strip()
    if not reply_text:
        await message.answer("❌ Текст не может быть пустым")
        return
    
    # Сохраняем данные
    data = load_data()
    data['reply_texts'].append(reply_text)
    data['set_by'] = message.from_user.id
    data['set_at'] = datetime.now().isoformat()
    save_data(data)
    
    await state.clear()
    
    await message.answer(
        f"✅ Текст добавлен в автоответы!\n\n"
        f"Текст: {reply_text}\n\n"
        f"Теперь после ответа пользователя на твои сообщения,\n"
        f"я буду отправлять случайный текст из списка с имитацией человека (задержка, typing)\n"
        f"Текущий список: {len(data['reply_texts'])} шт."
    )

# ==================== ОСНОВНАЯ ЛОГИКА ====================

@dp.message(F.text)
async def handle_private_message(message: types.Message):
    """
    Обрабатывает ВСЕ текстовые сообщения
    - Если от владельца: проверка на 'привет' -> стикер
    - Если от пользователя: автоответ текстом (если это ответ на сообщение владельца)
    """
    try:
        # Только личные сообщения
        if message.chat.type not in ['private', 'sender']:
            return
        
        if message.from_user.id == ADMIN_ID:
            # Сообщение от владельца: проверка триггера приветствия
            text = message.text.strip()
            if not text:
                return
            
            if is_trigger_message(text):
                logger.info(f"Триггер сработал: '{text}' в чате {message.chat.id}")
                
                # Задержка перед отправкой стикера
                delay = random.uniform(0.5, 2.0)
                await asyncio.sleep(delay)
                
                # Отправляем стикер
                await send_sticker_as_user(message.chat.id)
                
                logger.info(f"Стикер отправлен в ответ на '{text}'")
        
        else:
            # Сообщение от пользователя: проверяем, является ли это ответом на сообщение владельца
            if message.reply_to_message and message.reply_to_message.from_user.id == ADMIN_ID:
                logger.info(f"Ответ пользователя в чате {message.chat.id}")
                
                # Отправляем автоответ
                await send_auto_reply(message.chat.id)
    
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
    - Если от владельца: 'привет' -> стикер
    - Если от пользователя: автоответ если reply
    """
    try:
        if not hasattr(message, 'business_connection_id'):
            return
        
        business_id = message.business_connection_id
        
        if message.from_user.id == ADMIN_ID:
            # От владельца
            text = message.text.strip()
            if not text:
                return
            
            if is_trigger_message(text):
                logger.info(f"Бизнес-триггер: '{text}' в чате {message.chat.id}")
                
                # Задержка
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
                # Отправляем стикер
                data = load_data()
                sticker_id = data.get('sticker_id')
                
                if sticker_id:
                    await bot.send_sticker(
                        chat_id=message.chat.id,
                        sticker=sticker_id,
                        business_connection_id=business_id
                    )
                    
                    # Обновляем статистику
                    data['total_sent'] = data.get('total_sent', 0) + 1
                    data['last_used'] = datetime.now().isoformat()
                    save_data(data)
                    
                    logger.info(f"Бизнес-стикер отправлен")
        
        else:
            # От пользователя: проверка на reply
            if message.reply_to_message and message.reply_to_message.from_user.id == ADMIN_ID:
                await send_auto_reply(message.chat.id, business_id)
    
    except Exception as e:
        logger.error(f"Ошибка бизнес-обработки: {e}")

# ==================== ЗАПУСК БОТА ====================

async def main():
    """Запуск бота"""
    print("=" * 50)
    print("🤖 СТИКЕР-БОТ ДЛЯ TELEGRAM")
    print("Функция: автоматическая отправка стикера на 'привет' + случайный автоответ на ответы пользователей")
    print(f"👤 Владелец: {ADMIN_ID}")
    print("=" * 50)
    
    # Проверяем данные
    data = load_data()
    if data.get('sticker_id'):
        print(f"✅ Стикер установлен (отправлено: {data.get('total_sent', 0)})")
    else:
        print("⚠️ Стикер не установлен. Используй /setsticker")
    replies_count = len(data.get('reply_texts', []))
    if replies_count > 0:
        print(f"✅ Автоответы: {replies_count} шт.")
    else:
        print("⚠️ Автоответы не установлены. Используй /addreplytext")
    
    print("🔄 Бот запущен и слушает сообщения...")
    print("📝 Триггерные фразы:", ", ".join(TRIGGER_PHRASES[:5]) + "...")
    print("=" * 50)
    
    # Устанавливаем команды
    await bot.set_my_commands([
        types.BotCommand(command="start", description="Запустить бота"),
        types.BotCommand(command="setsticker", description="Установить стикер"),
        types.BotCommand(command="addreplytext", description="Добавить текст автоответа"),
        types.BotCommand(command="listreplies", description="Список автоответов"),
        types.BotCommand(command="removereply", description="Удалить автоответ"),
        types.BotCommand(command="clearreplies", description="Очистить автоответы"),
        types.BotCommand(command="stats", description="Статистика"),
        types.BotCommand(command="test", description="Тест стикера и автоответа")
    ])
    
    # Запускаем polling
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
