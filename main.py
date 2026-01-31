
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
REPLY_FILE = 'reply_tracker.json'  # Для отслеживания ответов

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

# ==================== СИСТЕМА ОТСЛЕЖИВАНИЯ ОТВЕТОВ ====================

def load_reply_data():
    """Загружает данные для отслеживания ответов"""
    if os.path.exists(REPLY_FILE):
        try:
            with open(REPLY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_reply_data(data):
    """Сохраняет данные для отслеживания ответов"""
    try:
        with open(REPLY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения reply данных: {e}")
        return False

def track_admin_message(chat_id, message_id):
    """Отслеживает сообщения админа для последующих ответов"""
    data = load_reply_data()
    
    if str(chat_id) not in data:
        data[str(chat_id)] = []
    
    # Храним только последние 50 сообщений в чате
    data[str(chat_id)] = data[str(chat_id)][-49:] + [message_id]
    
    # Очищаем старые чаты (старше 7 дней)
    # В реальности можно добавить timestamp для очистки
    if len(data) > 100:  # Храним максимум 100 чатов
        # Удаляем самые старые чаты
        pass
    
    save_reply_data(data)
    return True

def is_reply_to_admin(chat_id, reply_to_message_id):
    """Проверяет, является ли ответ на сообщение админа"""
    data = load_reply_data()
    
    if str(chat_id) not in data:
        return False
    
    return reply_to_message_id in data[str(chat_id)]

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================

def load_data():
    """Загружает сохраненные данные"""
    default_data = {
        'sticker_id': None,
        'owner_id': ADMIN_ID,
        'last_used': None,
        'total_sent': 0,
        'reply_mode': True,  # Включен ли режим ответов
        'delay_min': 0.5,    # Минимальная задержка
        'delay_max': 2.0     # Максимальная задержка
    }
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                default_data.update(loaded)
                return default_data
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
    
    return default_data

def save_data(data):
    """Сохраняет данные"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")
        return False

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

async def send_sticker_as_user(chat_id, business_connection_id=None):
    """Отправляет стикер от имени пользователя"""
    data = load_data()
    sticker_id = data.get('sticker_id')
    
    if not sticker_id:
        logger.warning("ID стикера не установлен")
        return False
    
    try:
        # Задержка (имитация человека)
        delay_min = data.get('delay_min', 0.5)
        delay_max = data.get('delay_max', 2.0)
        await asyncio.sleep(random.uniform(delay_min, delay_max))
        
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
    reply_mode = "✅ Включен" if data.get('reply_mode', True) else "❌ Выключен"
    total_sent = data.get('total_sent', 0)
    last_used = data.get('last_used', 'никогда')
    
    await message.answer(
        f"👋 <b>Стикер-бот запущен</b>\n\n"
        f"📊 <b>Статус:</b> {sticker_status}\n"
        f"🔄 <b>Режим ответов:</b> {reply_mode}\n"
        f"📨 <b>Отправлено стикеров:</b> {total_sent}\n"
        f"⏰ <b>Последняя отправка:</b> {last_used}\n\n"
        f"<b>Как использовать:</b>\n"
        f"1. Отправь мне стикер командой /setsticker\n"
        f"2. Пиши людям 'привет' в личных сообщениях\n"
        f"3. Бот автоматически отправит твой стикер\n"
        f"4. <b>НОВОЕ:</b> Когда человек отвечает на твоё сообщение, бот тоже отправит стикер!\n\n"
        f"<b>Команды:</b>\n"
        f"/setsticker - установить стикер\n"
        f"/reply on/off - вкл/выкл режим ответов\n"
        f"/delay 0.5-5 - установить задержку\n"
        f"/stats - статистика\n"
        f"/test - тест стикера"
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
        "После этого буду отправлять его от твоего лица когда:\n"
        "1. Ты пишешь 'привет' кому-то\n"
        "2. Человек отвечает на твоё сообщение"
    )

@dp.message(Command("reply"))
async def cmd_reply_mode(message: types.Message):
    """Включение/выключение режима ответов"""
    if message.from_user.id != ADMIN_ID:
        return
    
    args = message.text.split()
    data = load_data()
    
    if len(args) < 2:
        current = "включен" if data.get('reply_mode', True) else "выключен"
        await message.answer(f"📨 <b>Режим ответов:</b> {current}\n\nИспользуй: /reply on или /reply off")
        return
    
    mode = args[1].lower()
    if mode in ['on', 'вкл', 'да', '1', 'true']:
        data['reply_mode'] = True
        save_data(data)
        await message.answer("✅ <b>Режим ответов включен!</b>\n\nТеперь бот будет отправлять стикеры, когда люди отвечают на твои сообщения.")
    elif mode in ['off', 'выкл', 'нет', '0', 'false']:
        data['reply_mode'] = False
        save_data(data)
        await message.answer("❌ <b>Режим ответов выключен.</b>\n\nБот не будет реагировать на ответы пользователей.")
    else:
        await message.answer("⚠️ Используй: /reply on или /reply off")

@dp.message(Command("delay"))
async def cmd_delay(message: types.Message):
    """Установка задержки отправки"""
    if message.from_user.id != ADMIN_ID:
        return
    
    args = message.text.split()
    data = load_data()
    
    if len(args) < 2:
        current_min = data.get('delay_min', 0.5)
        current_max = data.get('delay_max', 2.0)
        await message.answer(
            f"⏱️ <b>Текущая задержка:</b> {current_min}-{current_max} секунд\n\n"
            f"Используй: /delay 1.5 (установит 1.5-2.5 сек)\n"
            f"Или: /delay 0.5 3 (установит 0.5-3 сек)"
        )
        return
    
    try:
        if len(args) == 2:
            # Один аргумент - устанавливаем min, max = min + 1
            delay = float(args[1])
            if 0.1 <= delay <= 10:
                data['delay_min'] = delay
                data['delay_max'] = delay + 1.0
                save_data(data)
                await message.answer(f"✅ <b>Задержка установлена:</b> {delay}-{delay+1} секунд")
            else:
                await message.answer("⚠️ Задержка должна быть от 0.1 до 10 секунд")
        elif len(args) == 3:
            # Два аргумента - min и max
            delay_min = float(args[1])
            delay_max = float(args[2])
            if 0.1 <= delay_min <= delay_max <= 10:
                data['delay_min'] = delay_min
                data['delay_max'] = delay_max
                save_data(data)
                await message.answer(f"✅ <b>Задержка установлена:</b> {delay_min}-{delay_max} секунд")
            else:
                await message.answer("⚠️ Задержка должна быть от 0.1 до 10 секунд, и min ≤ max")
    except ValueError:
        await message.answer("⚠️ Укажи число, например: /delay 1.5")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Статистика бота"""
    if message.from_user.id != ADMIN_ID:
        return
    
    data = load_data()
    sticker_id = data.get('sticker_id', 'не установлен')
    reply_mode = "✅ ВКЛ" if data.get('reply_mode', True) else "❌ ВЫКЛ"
    delay_min = data.get('delay_min', 0.5)
    delay_max = data.get('delay_max', 2.0)
    
    # Статистика по отслеживаемым чатам
    reply_data = load_reply_data()
    tracked_chats = len(reply_data)
    total_messages = sum(len(msgs) for msgs in reply_data.values())
    
    if sticker_id != 'не установлен':
        try:
            # Показываем превью стикера
            await message.answer_sticker(sticker_id)
        except:
            pass
    
    await message.answer(
        f"📊 <b>Статистика бота</b>\n\n"
        f"🆔 <b>ID стикера:</b>\n<code>{sticker_id[:50]}...</code>\n"
        f"🔄 <b>Режим ответов:</b> {reply_mode}\n"
        f"⏱️ <b>Задержка:</b> {delay_min}-{delay_max} сек\n"
        f"📨 <b>Всего отправлено:</b> {data.get('total_sent', 0)}\n"
        f"⏰ <b>Последняя отправка:</b> {data.get('last_used', 'никогда')}\n\n"
        f"<b>Отслеживание ответов:</b>\n"
        f"👥 Чатов отслеживается: {tracked_chats}\n"
        f"📝 Сообщений в памяти: {total_messages}\n\n"
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

@dp.message(Command("clear"))
async def cmd_clear(message: types.Message):
    """Очистка отслеживаемых чатов"""
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        # Создаем пустой файл
        with open(REPLY_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        await message.answer("✅ Данные отслеживания очищены!")
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
        f"Теперь когда:\n"
        f"1. Ты пишешь 'привет' в личных сообщениях\n"
        f"2. Человек отвечает на твоё сообщение\n"
        f"Я буду отправлять этот стикер от твоего лица!"
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
        
        # Сохраняем ID сообщения для отслеживания ответов
        track_admin_message(message.chat.id, message.message_id)
        logger.info(f"Сообщение админа сохранено: chat_id={message.chat.id}, msg_id={message.message_id}")
        
        # Проверяем на триггерные фразы
        if is_trigger_message(text):
            logger.info(f"Триггер сработал: '{text}' в чате {message.chat.id}")
            
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

# ==================== ОБРАБОТКА ОТВЕТОВ ПОЛЬЗОВАТЕЛЕЙ ====================

@dp.message(F.text)
async def handle_user_reply(message: types.Message):
    """
    Обрабатывает ответы пользователей на сообщения админа
    """
    try:
        # Только сообщения НЕ от админа
        if message.from_user.id == ADMIN_ID:
            return
        
        # Только личные сообщения
        if message.chat.type not in ['private', 'sender']:
            return
        
        # Проверяем, включен ли режим ответов
        data = load_data()
        if not data.get('reply_mode', True):
            return
        
        # Проверяем, является ли это ответом на сообщение
        if not message.reply_to_message:
            return
        
        # Проверяем, является ли ответ на сообщение админа
        reply_to_msg_id = message.reply_to_message.message_id
        chat_id = message.chat.id
        
        if is_reply_to_admin(chat_id, reply_to_msg_id):
            logger.info(f"Пользователь ответил на сообщение админа в чате {chat_id}")
            
            # Отправляем стикер
            await send_sticker_as_user(chat_id)
            
            logger.info(f"Стикер отправлен в ответ на реплай пользователя")
        else:
            logger.debug(f"Ответ не на сообщение админа или чат не отслеживается: {chat_id}")
    
    except Exception as e:
        logger.error(f"Ошибка обработки ответа пользователя: {e}")

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
        
        # Сохраняем ID сообщения для отслеживания ответов
        track_admin_message(message.chat.id, message.message_id)
        
        # Проверяем текст
        text = message.text.strip()
        if not text:
            return
        
        # Проверяем триггерные фразы
        if is_trigger_message(text):
            logger.info(f"Бизнес-триггер: '{text}' в чате {message.chat.id}")
            
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
    print("Функция 1: автоматическая отправка стикера когда ты пишешь 'привет'")
    print("Функция 2: отправка стикера когда человек отвечает на твоё сообщение")
    print(f"👤 Владелец: {ADMIN_ID}")
    print("=" * 50)
    
    # Проверяем данные
    data = load_data()
    if data.get('sticker_id'):
        print(f"✅ Стикер установлен (отправлено: {data.get('total_sent', 0)})")
        print(f"🔄 Режим ответов: {'ВКЛ' if data.get('reply_mode', True) else 'ВЫКЛ'}")
    else:
        print("⚠️ Стикер не установлен. Используй /setsticker")
    
    reply_data = load_reply_data()
    print(f"👥 Отслеживается чатов: {len(reply_data)}")
    
    print("🔄 Бот запущен и слушает сообщения...")
    print("📝 Триггерные фразы:", ", ".join(TRIGGER_PHRASES[:5]) + "...")
    print("=" * 50)
    
    # Устанавливаем команды
    await bot.set_my_commands([
        types.BotCommand(command="start", description="Запустить бота"),
        types.BotCommand(command="setsticker", description="Установить стикер"),
        types.BotCommand(command="reply", description="Режим ответов on/off"),
        types.BotCommand(command="delay", description="Установить задержку"),
        types.BotCommand(command="stats", description="Статистика"),
        types.BotCommand(command="test", description="Тест стикера"),
        types.BotCommand(command="clear", description="Очистить отслеживание")
    ])
    
    # Запускаем polling
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
