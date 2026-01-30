

import os
import json
import asyncio
import logging
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from dotenv import load_dotenv

# ==================== НАСТРОЙКИ ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

# Файлы данных
DATA_FILE = 'sticker_bot_data.json'
REPLIES_FILE = 'auto_replies.json'

# Инициализация бота с красивым дизайном
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode="HTML",
        link_preview_is_disabled=True
    )
)
dp = Dispatcher(storage=MemoryStorage())

# ==================== ДИЗАЙН ====================
class Design:
    """Класс для красивого оформления"""
    
    @staticmethod
    def header(text: str) -> str:
        """Заголовок"""
        return f"<b>✨ {text}</b>\n"
    
    @staticmethod
    def section(text: str) -> str:
        """Секция"""
        return f"<b>▫️ {text}</b>\n"
    
    @staticmethod
    def success(text: str) -> str:
        """Успех"""
        return f"✅ <b>{text}</b>"
    
    @staticmethod
    def warning(text: str) -> str:
        """Предупреждение"""
        return f"⚠️ <b>{text}</b>"
    
    @staticmethod
    def error(text: str) -> str:
        """Ошибка"""
        return f"❌ <b>{text}</b>"
    
    @staticmethod
    def info(text: str) -> str:
        """Информация"""
        return f"ℹ️ <b>{text}</b>"
    
    @staticmethod
    def online_status() -> str:
        """Онлайн статус"""
        status = random.choice(["🟢", "🟡", "🔵"])
        return f"{status} <i>онлайн</i>"
    
    @staticmethod
    def divider() -> str:
        """Разделитель"""
        return "─" * 35

# ==================== СОСТОЯНИЯ FSM ====================
class BotStates(StatesGroup):
    waiting_for_sticker = State()
    waiting_for_reply = State()
    waiting_for_delay = State()
    waiting_for_status = State()

# ==================== ФРАЗЫ-ТРИГГЕРЫ ====================
TRIGGER_PHRASES = [
    'привет', 'прив', 'хай', 'хей', 'hello', 'hi', 'hey',
    'здравствуй', 'здравствуйте', 'добрый день', 'доброе утро',
    'добрый вечер', 'салют', 'ку', 'здарова', 'приветствую',
    'приветик', 'здорово', 'приффки', 'хаюшки'
]

# ==================== РАБОТА С ДАННЫМИ ====================
def load_data():
    """Загружает данные бота"""
    default_data = {
        'sticker_id': None,
        'owner_id': ADMIN_ID,
        'total_sent': 0,
        'replies_sent': 0,
        'status': '🟢 Активный',
        'last_active': datetime.now().isoformat(),
        'auto_replies': [
            "Да, слушаю тебя)",
            "Норм, а у тебя как?",
            "Че по чем?)",
            "Го общаться)",
            "Что нового?",
            "Как дела?)",
            "Рассказывай)",
            "Интересно)",
            "Понял тебя)",
            "Ага, продолжа)"
        ],
        'cooldown': {
            'min': 10,
            'max': 30
        },
        'settings': {
            'auto_reply': True,
            'send_stickers': True,
            'typing_simulation': True,
            'read_simulation': True
        }
    }
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                # Объединяем с дефолтными значениями
                for key in default_data:
                    if key not in saved:
                        saved[key] = default_data[key]
                return saved
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
    
    return default_data

def save_data(data):
    """Сохраняет данные бота"""
    try:
        data['last_active'] = datetime.now().isoformat()
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения: {e}")
        return False

# ==================== КЛАВИАТУРЫ ====================
def get_main_menu():
    """Главное меню с кнопками"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎯 Главная"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📝 Автоответы")],
            [KeyboardButton(text="🎨 Дизайн"), KeyboardButton(text="🆘 Помощь")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )

def get_settings_menu():
    """Меню настроек"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎭 Изменить стикер", callback_data="change_sticker"),
                InlineKeyboardButton(text="⏱️ Изменить задержки", callback_data="change_delay")
            ],
            [
                InlineKeyboardButton(text="🤖 Автоответы", callback_data="toggle_replies"),
                InlineKeyboardButton(text="🎨 Стикеры", callback_data="toggle_stickers")
            ],
            [
                InlineKeyboardButton(text="⌨️ Печатание", callback_data="toggle_typing"),
                InlineKeyboardButton(text="👀 Чтение", callback_data="toggle_reading")
            ],
            [
                InlineKeyboardButton(text="📱 Статус", callback_data="change_status"),
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
            ]
        ]
    )

def get_replies_menu():
    """Меню автоответов"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить ответ", callback_data="add_reply"),
                InlineKeyboardButton(text="🗑️ Удалить ответ", callback_data="delete_reply")
            ],
            [
                InlineKeyboardButton(text="📋 Список ответов", callback_data="list_replies"),
                InlineKeyboardButton(text="🎲 Случайный режим", callback_data="random_mode")
            ],
            [
                InlineKeyboardButton(text="🔄 Сбросить", callback_data="reset_replies"),
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
            ]
        ]
    )

def get_status_menu():
    """Меню статусов"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Активный", callback_data="status_active"),
                InlineKeyboardButton(text="🟡 Не беспокоить", callback_data="status_dnd")
            ],
            [
                InlineKeyboardButton(text="🔴 Офлайн", callback_data="status_offline"),
                InlineKeyboardButton(text="💤 Спит", callback_data="status_sleep")
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_settings")]
        ]
    )

def get_back_button():
    """Кнопка назад"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ]
    )

# ==================== УТИЛИТЫ ====================
def is_trigger_message(text):
    """Проверяет триггерные фразы"""
    if not text:
        return False
    
    text_lower = text.strip().lower()
    
    for phrase in TRIGGER_PHRASES:
        if phrase == text_lower:
            return True
        if phrase in text_lower and len(text_lower) < 30:
            return True
    
    return False

async def simulate_typing(chat_id, duration=2):
    """Имитация печатания"""
    data = load_data()
    if data['settings']['typing_simulation']:
        await asyncio.sleep(duration)
        # В реальном боте здесь был бы bot.send_chat_action

async def simulate_reading(chat_id, duration=1):
    """Имитация чтения"""
    data = load_data()
    if data['settings']['read_simulation']:
        await asyncio.sleep(duration)

async def send_sticker_as_user(chat_id, business_connection_id=None):
    """Отправляет стикер от лица пользователя"""
    data = load_data()
    
    if not data['settings']['send_stickers'] or not data.get('sticker_id'):
        return False
    
    try:
        if business_connection_id:
            await bot.send_sticker(
                chat_id=chat_id,
                sticker=data['sticker_id'],
                business_connection_id=business_connection_id
            )
        else:
            await bot.send_sticker(
                chat_id=chat_id,
                sticker=data['sticker_id']
            )
        
        # Обновляем статистику
        data['total_sent'] += 1
        save_data(data)
        
        logger.info(f"🎯 Стикер отправлен в чат {chat_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки стикера: {e}")
        return False

async def send_auto_reply(chat_id, user_message, business_connection_id=None):
    """Отправляет автоответ"""
    data = load_data()
    
    if not data['settings']['auto_reply'] or not data['auto_replies']:
        return False
    
    try:
        # Выбираем случайный ответ
        reply_text = random.choice(data['auto_replies'])
        
        # Имитация чтения сообщения
        await simulate_reading(chat_id, random.uniform(0.5, 1.5))
        
        # Имитация печатания (пропорционально длине ответа)
        typing_time = len(reply_text) * 0.05
        await simulate_typing(chat_id, min(typing_time, 3))
        
        # Отправляем ответ
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
        
        # Обновляем статистику
        data['replies_sent'] += 1
        save_data(data)
        
        logger.info(f"💬 Автоответ отправлен: {reply_text[:30]}...")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка автоответа: {e}")
        return False

# ==================== КОМАНДЫ ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда /start"""
    if message.from_user.id != ADMIN_ID:
        await message.answer(
            Design.error("Этот бот доступен только владельцу"),
            reply_markup=get_back_button()
        )
        return
    
    data = load_data()
    
    welcome_text = (
        Design.header("SMART STICKER BOT") + "\n"
        f"{Design.online_status()}\n"
        f"{Design.divider()}\n"
        f"{Design.section('Основные функции:')}\n"
        "• 🎯 Автостикеры при приветствии\n"
        "• 💬 Умные автоответы\n"
        "• ⏱️ Реалистичные задержки\n"
        "• ⌨️ Имитация печатания\n\n"
        f"{Design.section('Статистика:')}\n"
        f"📊 Стикеров отправлено: <b>{data['total_sent']}</b>\n"
        f"💬 Автоответов: <b>{data['replies_sent']}</b>\n"
        f"🎭 Статус: {data['status']}\n\n"
        f"{Design.info('Используйте меню ниже для управления')}"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

@dp.message(F.text == "🎯 Главная")
async def cmd_main(message: types.Message):
    """Главное меню"""
    if message.from_user.id != ADMIN_ID:
        return
    
    data = load_data()
    
    status_text = (
        Design.header("Главная панель") + "\n"
        f"{Design.online_status()}\n"
        f"{Design.divider()}\n"
        f"🆔 <b>Ваш ID:</b> <code>{ADMIN_ID}</code>\n"
        f"🎭 <b>Статус:</b> {data['status']}\n"
        f"📊 <b>Активность:</b>\n"
        f"  • Стикеров: <b>{data['total_sent']}</b>\n"
        f"  • Ответов: <b>{data['replies_sent']}</b>\n\n"
        f"⚙️ <b>Настройки:</b>\n"
        f"  • Автоответы: {'✅' if data['settings']['auto_reply'] else '❌'}\n"
        f"  • Стикеры: {'✅' if data['settings']['send_stickers'] else '❌'}\n"
        f"  • Печатание: {'✅' if data['settings']['typing_simulation'] else '❌'}\n"
        f"  • Чтение: {'✅' if data['settings']['read_simulation'] else '❌'}\n\n"
        f"{Design.info('Выберите раздел в меню 👇')}"
    )
    
    await message.answer(
        status_text,
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

@dp.message(F.text == "⚙️ Настройки")
async def cmd_settings(message: types.Message):
    """Настройки бота"""
    if message.from_user.id != ADMIN_ID:
        return
    
    data = load_data()
    
    settings_text = (
        Design.header("Настройки бота") + "\n"
        f"{Design.divider()}\n"
        f"⚙️ <b>Текущие настройки:</b>\n\n"
        f"<b>Автоответы:</b> {'✅ ВКЛ' if data['settings']['auto_reply'] else '❌ ВЫКЛ'}\n"
        f"<b>Стикеры:</b> {'✅ ВКЛ' if data['settings']['send_stickers'] else '❌ ВЫКЛ'}\n"
        f"<b>Печатание:</b> {'✅ Имитация' if data['settings']['typing_simulation'] else '❌ Нет'}\n"
        f"<b>Чтение:</b> {'✅ Имитация' if data['settings']['read_simulation'] else '❌ Нет'}\n\n"
        f"⏱️ <b>Задержки ответов:</b>\n"
        f"• Минимум: <b>{data['cooldown']['min']} сек</b>\n"
        f"• Максимум: <b>{data['cooldown']['max']} сек</b>\n\n"
        f"{Design.info('Используйте кнопки ниже для изменения 👇')}"
    )
    
    await message.answer(
        settings_text,
        reply_markup=get_settings_menu(),
        parse_mode="HTML"
    )

@dp.message(F.text == "📊 Статистика")
async def cmd_stats(message: types.Message):
    """Статистика"""
    if message.from_user.id != ADMIN_ID:
        return
    
    data = load_data()
    
    stats_text = (
        Design.header("📊 Статистика бота") + "\n"
        f"{Design.divider()}\n"
        f"🎯 <b>Основная статистика:</b>\n"
        f"• Стикеров отправлено: <b>{data['total_sent']}</b>\n"
        f"• Автоответов отправлено: <b>{data['replies_sent']}</b>\n"
        f"• Всего сообщений: <b>{data['total_sent'] + data['replies_sent']}</b>\n\n"
        
        f"⚙️ <b>Настройки активности:</b>\n"
        f"• Автоответы: {'✅' if data['settings']['auto_reply'] else '❌'}\n"
        f"• Стикеры: {'✅' if data['settings']['send_stickers'] else '❌'}\n"
        f"• Режим: {data['status']}\n\n"
        
        f"📅 <b>Активность:</b>\n"
        f"• Последняя активность: {data.get('last_active', 'никогда')}\n"
        f"• Стикер установлен: {'✅' if data.get('sticker_id') else '❌'}\n"
        f"• Ответов в базе: <b>{len(data['auto_replies'])}</b>\n\n"
        
        f"{Design.success('Бот работает стабильно!')}"
    )
    
    await message.answer(
        stats_text,
        reply_markup=get_back_button(),
        parse_mode="HTML"
    )

@dp.message(F.text == "📝 Автоответы")
async def cmd_replies(message: types.Message):
    """Управление автоответами"""
    if message.from_user.id != ADMIN_ID:
        return
    
    data = load_data()
    
    replies_text = (
        Design.header("📝 Автоответы") + "\n"
        f"{Design.divider()}\n"
        f"🔢 <b>Всего ответов:</b> <code>{len(data['auto_replies'])}</code>\n"
        f"📨 <b>Отправлено:</b> <code>{data['replies_sent']}</code>\n\n"
        
        f"📋 <b>Последние 5 ответов:</b>\n"
    )
    
    # Показываем последние 5 ответов
    for i, reply in enumerate(data['auto_replies'][-5:], 1):
        replies_text += f"{i}. {reply[:30]}...\n"
    
    replies_text += f"\n{Design.info('Управляйте ответами через кнопки 👇')}"
    
    await message.answer(
        replies_text,
        reply_markup=get_replies_menu(),
        parse_mode="HTML"
    )

@dp.message(F.text == "🎨 Дизайн")
async def cmd_design(message: types.Message):
    """Настройки дизайна"""
    if message.from_user.id != ADMIN_ID:
        return
    
    design_text = (
        Design.header("🎨 Дизайн и внешний вид") + "\n"
        f"{Design.divider()}\n"
        "✨ <b>Текущая тема:</b> Современная темная\n"
        "🎭 <b>Стиль:</b> Минимализм\n"
        "🌈 <b>Цветовая схема:</b> Синий акцент\n\n"
        
        "🛠️ <b>Доступные опции:</b>\n"
        "• Изменение цветовой схемы\n"
        "• Смена иконок статуса\n"
        "• Настройка шрифтов\n"
        "• Кастомные разделители\n\n"
        
        f"{Design.warning('В разработке...')}\n"
        f"{Design.info('Скоро будут новые фичи!')}"
    )
    
    await message.answer(
        design_text,
        reply_markup=get_back_button(),
        parse_mode="HTML"
    )

@dp.message(F.text == "🆘 Помощь")
async def cmd_help(message: types.Message):
    """Помощь"""
    if message.from_user.id != ADMIN_ID:
        return
    
    help_text = (
        Design.header("🆘 Помощь и инструкции") + "\n"
        f"{Design.divider()}\n"
        
        "🎯 <b>Как работает бот:</b>\n"
        "1. Когда вы пишете 'привет' - бот отправляет стикер\n"
        "2. Когда вам отвечают - бот отправляет автоответ\n"
        "3. Все с реалистичными задержками\n\n"
        
        "⚙️ <b>Основные команды:</b>\n"
        "• /start - Запустить бота\n"
        "• /setsticker - Установить стикер\n"
        "• /test - Тест работы\n\n"
        
        "📱 <b>Разделы меню:</b>\n"
        "• 🎯 Главная - Общая информация\n"
        "• ⚙️ Настройки - Настройка функций\n"
        "• 📊 Статистика - Статистика работы\n"
        "• 📝 Автоответы - Управление ответами\n"
        "• 🎨 Дизайн - Настройка внешнего вида\n\n"
        
        f"{Design.success('Бот работает в фоне 24/7')}\n"
        f"{Design.info('По вопросам: t.me/fuck_zaza')}"
    )
    
    await message.answer(
        help_text,
        reply_markup=get_back_button(),
        parse_mode="HTML"
    )

# ==================== CALLBACK HANDLERS ====================
@dp.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: types.CallbackQuery):
    """Возврат в главное меню"""
    await cmd_main(callback.message)

@dp.callback_query(F.data == "back_to_settings")
async def callback_back_to_settings(callback: types.CallbackQuery):
    """Возврат в настройки"""
    await cmd_settings(callback.message)

@dp.callback_query(F.data == "change_sticker")
async def callback_change_sticker(callback: types.CallbackQuery, state: FSMContext):
    """Смена стикера"""
    await state.set_state(BotStates.waiting_for_sticker)
    await callback.message.edit_text(
        Design.header("🎭 Смена стикера") + "\n"
        f"{Design.divider()}\n"
        f"{Design.info('Отправьте мне новый стикер для автоотправки')}\n\n"
        "📎 <b>Инструкция:</b>\n"
        "1. Найдите нужный стикер\n"
        "2. Отправьте его в этот чат\n"
        "3. Бот сохранит его ID\n\n"
        f"{Design.warning('Стикер должен быть из доступных наборов')}",
        reply_markup=get_back_button(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "toggle_replies")
async def callback_toggle_replies(callback: types.CallbackQuery):
    """Включение/выключение автоответов"""
    data = load_data()
    data['settings']['auto_reply'] = not data['settings']['auto_reply']
    save_data(data)
    
    status = "✅ ВКЛЮЧЕНЫ" if data['settings']['auto_reply'] else "❌ ВЫКЛЮЧЕНЫ"
    await callback.answer(f"Автоответы: {status}")
    await cmd_settings(callback.message)

# ==================== ОСНОВНАЯ ЛОГИКА ====================
@dp.message(BotStates.waiting_for_sticker, F.sticker)
async def process_sticker_input(message: types.Message, state: FSMContext):
    """Обработка нового стикера"""
    if message.from_user.id != ADMIN_ID:
        return
    
    sticker = message.sticker
    data = load_data()
    data['sticker_id'] = sticker.file_id
    save_data(data)
    
    await state.clear()
    
    # Показываем стикер
    await message.answer_sticker(sticker.file_id)
    
    await message.answer(
        Design.success("Стикер успешно сохранен!") + "\n\n"
        f"🎭 <b>Информация:</b>\n"
        f"• Emoji: {sticker.emoji or 'нет'}\n"
        f"• Набор: {sticker.set_name or 'нет'}\n"
        f"• ID: <code>{sticker.file_id[:30]}...</code>\n\n"
        f"{Design.info('Теперь бот будет отправлять этот стикер автоматически')}",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

@dp.message(F.text)
async def handle_private_message(message: types.Message):
    """
    Основная логика: когда ты пишешь "привет", бот отправляет стикер
    """
    try:
        # Только сообщения от владельца
        if message.from_user.id != ADMIN_ID:
            return
        
        # Только личные сообщения
        if message.chat.type not in ['private', 'sender']:
            return
        
        text = message.text.strip()
        if not text:
            return
        
        # Проверяем триггер
        if is_trigger_message(text):
            logger.info(f"🎯 Триггер: '{text}' в чате {message.chat.id}")
            
            # Небольшая задержка
            await asyncio.sleep(random.uniform(0.3, 1.2))
            
            # Отправляем стикер
            await send_sticker_as_user(message.chat.id)
            
            logger.info(f"✅ Стикер отправлен на '{text}'")
    
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

@dp.business_message(F.text)
async def handle_business_text(message: types.Message):
    """
    Обработка бизнес-сообщений
    """
    try:
        if not hasattr(message, 'business_connection_id'):
            return
        
        # Только от владельца
        if message.from_user.id != ADMIN_ID:
            return
        
        text = message.text.strip()
        if not text:
            return
        
        # Проверяем триггер
        if is_trigger_message(text):
            logger.info(f"🏢 Бизнес-триггер: '{text}'")
            
            await asyncio.sleep(random.uniform(0.3, 1.2))
            
            data = load_data()
            if data['settings']['send_stickers'] and data.get('sticker_id'):
                await bot.send_sticker(
                    chat_id=message.chat.id,
                    sticker=data['sticker_id'],
                    business_connection_id=message.business_connection_id
                )
                data['total_sent'] += 1
                save_data(data)
    
    except Exception as e:
        logger.error(f"❌ Бизнес-ошибка: {e}")

# ==================== ЗАПУСК БОТА ====================
async def set_bot_commands():
    """Установка команд бота"""
    commands = [
        types.BotCommand(command="start", description="🚀 Запустить бота"),
        types.BotCommand(command="setsticker", description="🎭 Установить стикер"),
        types.BotCommand(command="test", description="🧪 Тест работы"),
        types.BotCommand(command="help", description="🆘 Помощь")
    ]
    await bot.set_my_commands(commands)

async def main():
    """Запуск бота"""
    print("=" * 60)
    print("🤖 SMART STICKER BOT - TELEGRAM")
    print("✨ Автоответы с дизайном и кнопками")
    print(f"👤 Владелец: {ADMIN_ID}")
    print("=" * 60)
    
    # Загружаем данные
    data = load_data()
    print(f"🎭 Стикер: {'✅' if data.get('sticker_id') else '❌'}")
    print(f"💬 Автоответов: {len(data['auto_replies'])}")
    print(f"📊 Отправлено: {data['total_sent']} стикеров")
    print("=" * 60)
    print("🔄 Бот запущен...")
    print("📱 Используйте меню для управления")
    print("=" * 60)
    
    # Устанавливаем команды
    await set_bot_commands()
    
    # Запускаем
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
