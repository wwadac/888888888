"""
УЛУЧШЕННЫЙ СТИКЕР-БОТ ДЛЯ TELEGRAM
Функции:
1. Автоматическая отправка стикера при фразе "привет"
2. Система команд с инлайн-кнопками
3. Возможность создавать/удалять команды
4. Удаление исходной команды (.топ) при использовании
Автор: t.me/fuck_zaza
"""

import os
import json
import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, List
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
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

# Файлы для хранения данных
STICKER_DATA_FILE = 'sticker_bot_data.json'
COMMANDS_DATA_FILE = 'bot_commands.json'

# Инициализация бота
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher(storage=MemoryStorage())

# Состояния FSM
class StickerStates(StatesGroup):
    waiting_for_sticker = State()

class CommandStates(StatesGroup):
    waiting_for_command_name = State()
    waiting_for_command_trigger = State()
    waiting_for_command_response = State()
    waiting_for_command_edit = State()

# Триггерные фразы для приветствия
TRIGGER_PHRASES = [
    'привет', 'прив', 'хай', 'хей', 'hello', 'hi', 'hey',
    'здравствуй', 'здравствуйте', 'добрый день', 'доброе утро',
    'добрый вечер', 'салют', 'ку', 'здарова', 'приветствую',
    'приветик', 'здорово'
]

# ==================== СИСТЕМА КОМАНД ====================

def load_commands() -> Dict:
    """Загружает сохраненные команды"""
    default_commands = {
        'commands': [],
        'last_update': None
    }
    
    if os.path.exists(COMMANDS_DATA_FILE):
        try:
            with open(COMMANDS_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки команд: {e}")
    
    return default_commands

def save_commands(data: Dict) -> bool:
    """Сохраняет команды"""
    try:
        data['last_update'] = datetime.now().isoformat()
        with open(COMMANDS_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения команд: {e}")
        return False

def load_sticker_data() -> Dict:
    """Загружает данные стикера"""
    default_data = {
        'sticker_id': None,
        'owner_id': ADMIN_ID,
        'last_used': None,
        'total_sent': 0
    }
    
    if os.path.exists(STICKER_DATA_FILE):
        try:
            with open(STICKER_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки данных стикера: {e}")
    
    return default_data

def save_sticker_data(data: Dict) -> bool:
    """Сохраняет данные стикера"""
    try:
        with open(STICKER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения данных стикера: {e}")
        return False

# ==================== ИНЛАЙН-КЛАВИАТУРЫ ====================

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню бота"""
    keyboard = [
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="menu_stats"),
            InlineKeyboardButton(text="🎨 Установить стикер", callback_data="menu_set_sticker")
        ],
        [
            InlineKeyboardButton(text="📝 Управление командами", callback_data="menu_commands"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_settings")
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_refresh"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="menu_help")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_commands_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню управления командами"""
    keyboard = [
        [
            InlineKeyboardButton(text="➕ Добавить команду", callback_data="cmd_add"),
            InlineKeyboardButton(text="📋 Список команд", callback_data="cmd_list")
        ],
        [
            InlineKeyboardButton(text="✏️ Редактировать", callback_data="cmd_edit"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data="cmd_delete")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="cmd_refresh")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_command_list_keyboard(commands: List[Dict]) -> InlineKeyboardMarkup:
    """Клавиатура со списком команд"""
    keyboard = []
    
    for i, cmd in enumerate(commands, 1):
        keyboard.append([
            InlineKeyboardButton(
                text=f"{i}. {cmd['name']} → {cmd['trigger']}",
                callback_data=f"cmd_view_{i-1}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_commands"),
        InlineKeyboardButton(text="➕ Добавить", callback_data="cmd_add")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_edit_command_keyboard(cmd_index: int) -> InlineKeyboardMarkup:
    """Клавиатура для редактирования команды"""
    keyboard = [
        [
            InlineKeyboardButton(text="✏️ Название", callback_data=f"cmd_edit_name_{cmd_index}"),
            InlineKeyboardButton(text="🔤 Триггер", callback_data=f"cmd_edit_trigger_{cmd_index}")
        ],
        [
            InlineKeyboardButton(text="💬 Ответ", callback_data=f"cmd_edit_response_{cmd_index}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"cmd_delete_confirm_{cmd_index}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="cmd_list"),
            InlineKeyboardButton(text="✅ Готово", callback_data="menu_commands")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_confirm_delete_keyboard(cmd_index: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"cmd_delete_execute_{cmd_index}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"cmd_view_{cmd_index}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда /start с инлайн-меню"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Этот бот доступен только владельцу")
        return
    
    welcome_text = (
        "👋 <b>Добро пожаловать в улучшенный Стикер-Бот!</b>\n\n"
        "✨ <b>Новые возможности:</b>\n"
        "✅ Система команд с инлайн-кнопками\n"
        "✅ Создание своих команд (например, .топ)\n"
        "✅ Удаление исходной команды при использовании\n"
        "✅ Красивое меню управления\n"
        "✅ Статистика и настройки\n\n"
        "🖱️ <b>Используй кнопки ниже для управления:</b>"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard())

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    """Показать главное меню"""
    if message.from_user.id != ADMIN_ID:
        return
    
    await message.answer("📱 <b>Главное меню</b>", reply_markup=get_main_menu_keyboard())

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Справка по боту"""
    help_text = (
        "🆘 <b>Справка по боту</b>\n\n"
        
        "🎯 <b>Основные функции:</b>\n"
        "1. Авто-отправка стикера при фразе 'привет'\n"
        "2. Создание своих команд (начинаются с точки)\n"
        "3. Удаление команды (.топ) при использовании\n"
        "4. Управление через инлайн-кнопки\n\n"
        
        "📝 <b>Примеры команд:</b>\n"
        "• <code>.топ</code> - удалится и отправит ответ\n"
        "• <code>.скидка</code> - удалится и отправит скидку\n"
        "• <code>.контакты</code> - удалится и отправит контакты\n\n"
        
        "⚙️ <b>Управление:</b>\n"
        "• Используй <code>/menu</code> для открытия меню\n"
        "• Используй инлайн-кнопки для настройки\n\n"
        
        "📞 <b>Поддержка:</b> @fuck_zaza"
    )
    
    await message.answer(help_text)

# ==================== ОБРАБОТКА ИНЛАЙН-КНОПОК ====================

@dp.callback_query(F.data == "menu_main")
async def handle_menu_main(callback: CallbackQuery):
    """Главное меню"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    await callback.message.edit_text("📱 <b>Главное меню</b>", reply_markup=get_main_menu_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "menu_stats")
async def handle_menu_stats(callback: CallbackQuery):
    """Статистика бота"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    sticker_data = load_sticker_data()
    commands_data = load_commands()
    
    # Получаем информацию о стикере
    sticker_status = "✅ Установлен" if sticker_data.get('sticker_id') else "❌ Не установлен"
    total_sent = sticker_data.get('total_sent', 0)
    last_used = sticker_data.get('last_used', 'никогда')
    total_commands = len(commands_data.get('commands', []))
    
    stats_text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"🎯 <b>Стикер:</b> {sticker_status}\n"
        f"📨 <b>Отправлено стикеров:</b> {total_sent}\n"
        f"⏰ <b>Последняя отправка:</b> {last_used}\n"
        f"📝 <b>Создано команд:</b> {total_commands}\n"
        f"👤 <b>Владелец:</b> {ADMIN_ID}\n\n"
        "<i>Используй кнопки ниже для управления</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_stats"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")
        ]
    ]
    
    await callback.message.edit_text(stats_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@dp.callback_query(F.data == "menu_set_sticker")
async def handle_menu_set_sticker(callback: CallbackQuery, state: FSMContext):
    """Установка стикера"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    await state.set_state(StickerStates.waiting_for_sticker)
    
    set_sticker_text = (
        "🎨 <b>Установка стикера</b>\n\n"
        "📎 Отправь мне любой стикер, и я сохраню его.\n"
        "После этого, когда ты будешь писать 'привет',\n"
        "я буду автоматически отправлять этот стикер.\n\n"
        "<i>Просто отправь стикер в этот чат...</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_sticker"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")
        ]
    ]
    
    await callback.message.edit_text(set_sticker_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@dp.callback_query(F.data == "menu_commands")
async def handle_menu_commands(callback: CallbackQuery):
    """Меню управления командами"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    commands_data = load_commands()
    total_commands = len(commands_data.get('commands', []))
    
    commands_text = (
        "📝 <b>Управление командами</b>\n\n"
        f"📊 Всего команд: {total_commands}\n\n"
        "<b>Доступные действия:</b>\n"
        "➕ Добавить новую команду\n"
        "📋 Посмотреть список команд\n"
        "✏️ Редактировать существующие\n"
        "🗑️ Удалить команды\n\n"
        "<i>Команды работают так: пишешь .команда → бот удаляет её и отправляет ответ</i>"
    )
    
    await callback.message.edit_text(commands_text, reply_markup=get_commands_menu_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "menu_settings")
async def handle_menu_settings(callback: CallbackQuery):
    """Настройки бота"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    settings_text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        "<b>Доступные настройки:</b>\n"
        "• Триггерные фразы для приветствия\n"
        "• Задержка перед отправкой стикера\n"
        "• Формат ответов команд\n"
        "• Авто-удаление команд\n\n"
        "<i>Настройки находятся в разработке...</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_settings"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")
        ]
    ]
    
    await callback.message.edit_text(settings_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@dp.callback_query(F.data == "menu_refresh")
async def handle_menu_refresh(callback: CallbackQuery):
    """Обновить меню"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    await callback.message.edit_text("📱 <b>Главное меню</b>", reply_markup=get_main_menu_keyboard())
    await callback.answer("✅ Меню обновлено")

@dp.callback_query(F.data == "menu_help")
async def handle_menu_help(callback: CallbackQuery):
    """Помощь"""
    help_text = (
        "❓ <b>Помощь и инструкции</b>\n\n"
        
        "🎯 <b>Как использовать:</b>\n"
        "1. Установи стикер через меню\n"
        "2. Создай нужные команды\n"
        "3. Пиши 'привет' или используй команды\n"
        "4. Команды (.топ) автоматически удаляются\n\n"
        
        "📝 <b>Создание команды:</b>\n"
        "1. Нажми 'Управление командами'\n"
        "2. Выбери 'Добавить команду'\n"
        "3. Введи название, триггер и ответ\n"
        "4. Готово! Команда работает\n\n"
        
        "💡 <b>Пример:</b>\n"
        "Название: Топ продаж\n"
        "Триггер: .топ\n"
        "Ответ: 🏆 Топ продаж этой недели...\n\n"
        
        "<i>При использовании .топ, бот удалит эту команду и отправит ответ</i>\n\n"
        
        "📞 <b>Поддержка:</b> @fuck_zaza"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main"),
            InlineKeyboardButton(text="📝 К командам", callback_data="menu_commands")
        ]
    ]
    
    await callback.message.edit_text(help_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

# ==================== УПРАВЛЕНИЕ КОМАНДАМИ ====================

@dp.callback_query(F.data == "cmd_add")
async def handle_cmd_add(callback: CallbackQuery, state: FSMContext):
    """Добавление новой команды"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    await state.set_state(CommandStates.waiting_for_command_name)
    await state.update_data(message_id=callback.message.message_id)
    
    add_text = (
        "➕ <b>Добавление новой команды</b>\n\n"
        "📝 <b>Шаг 1 из 3:</b> Введите название команды\n\n"
        "<i>Пример: 'Топ продаж', 'Акции', 'Контакты'</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cmd_cancel"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_commands")
        ]
    ]
    
    await callback.message.edit_text(add_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@dp.callback_query(F.data == "cmd_list")
async def handle_cmd_list(callback: CallbackQuery):
    """Список команд"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    commands_data = load_commands()
    commands = commands_data.get('commands', [])
    
    if not commands:
        list_text = (
            "📋 <b>Список команд</b>\n\n"
            "📭 У вас пока нет созданных команд.\n\n"
            "<i>Нажмите 'Добавить команду' чтобы создать первую</i>"
        )
    else:
        list_text = "📋 <b>Список команд</b>\n\n"
        for i, cmd in enumerate(commands, 1):
            list_text += f"{i}. <b>{cmd['name']}</b>\n"
            list_text += f"   Триггер: <code>{cmd['trigger']}</code>\n"
            list_text += f"   Ответ: {cmd['response'][:30]}...\n\n"
    
    await callback.message.edit_text(list_text, reply_markup=get_command_list_keyboard(commands))
    await callback.answer()

@dp.callback_query(F.data.startswith("cmd_view_"))
async def handle_cmd_view(callback: CallbackQuery):
    """Просмотр конкретной команды"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    cmd_index = int(callback.data.split("_")[2])
    commands_data = load_commands()
    commands = commands_data.get('commands', [])
    
    if cmd_index >= len(commands):
        await callback.answer("❌ Команда не найдена")
        return
    
    cmd = commands[cmd_index]
    
    view_text = (
        f"👁️ <b>Просмотр команды</b>\n\n"
        f"📝 <b>Название:</b> {cmd['name']}\n"
        f"🔤 <b>Триггер:</b> <code>{cmd['trigger']}</code>\n"
        f"💬 <b>Ответ:</b>\n{cmd['response']}\n\n"
        f"⏰ <b>Создана:</b> {cmd.get('created_at', 'неизвестно')}\n"
        f"📊 <b>Использований:</b> {cmd.get('usage_count', 0)}"
    )
    
    await callback.message.edit_text(view_text, reply_markup=get_edit_command_keyboard(cmd_index))
    await callback.answer()

@dp.callback_query(F.data == "cmd_edit")
async def handle_cmd_edit(callback: CallbackQuery):
    """Редактирование команд - показывает список"""
    await handle_cmd_list(callback)

@dp.callback_query(F.data.startswith("cmd_edit_name_"))
async def handle_cmd_edit_name(callback: CallbackQuery, state: FSMContext):
    """Редактирование названия команды"""
    cmd_index = int(callback.data.split("_")[3])
    await state.set_state(CommandStates.waiting_for_command_edit)
    await state.update_data(
        edit_type="name",
        cmd_index=cmd_index,
        message_id=callback.message.message_id
    )
    
    edit_text = (
        "✏️ <b>Редактирование команды</b>\n\n"
        "Введите новое название команды:"
    )
    
    await callback.message.edit_text(edit_text)
    await callback.answer("Введите новое название")

@dp.callback_query(F.data.startswith("cmd_edit_trigger_"))
async def handle_cmd_edit_trigger(callback: CallbackQuery, state: FSMContext):
    """Редактирование триггера команды"""
    cmd_index = int(callback.data.split("_")[3])
    await state.set_state(CommandStates.waiting_for_command_edit)
    await state.update_data(
        edit_type="trigger",
        cmd_index=cmd_index,
        message_id=callback.message.message_id
    )
    
    edit_text = (
        "✏️ <b>Редактирование команды</b>\n\n"
        "Введите новый триггер команды (начинается с точки):\n"
        "<i>Пример: .топ, .скидка, .контакты</i>"
    )
    
    await callback.message.edit_text(edit_text)
    await callback.answer("Введите новый триггер")

@dp.callback_query(F.data.startswith("cmd_edit_response_"))
async def handle_cmd_edit_response(callback: CallbackQuery, state: FSMContext):
    """Редактирование ответа команды"""
    cmd_index = int(callback.data.split("_")[3])
    await state.set_state(CommandStates.waiting_for_command_edit)
    await state.update_data(
        edit_type="response",
        cmd_index=cmd_index,
        message_id=callback.message.message_id
    )
    
    edit_text = (
        "✏️ <b>Редактирование команды</b>\n\n"
        "Введите новый ответ команды:"
    )
    
    await callback.message.edit_text(edit_text)
    await callback.answer("Введите новый ответ")

@dp.callback_query(F.data.startswith("cmd_delete_"))
async def handle_cmd_delete(callback: CallbackQuery):
    """Удаление команды"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    if callback.data.startswith("cmd_delete_confirm_"):
        cmd_index = int(callback.data.split("_")[3])
        commands_data = load_commands()
        commands = commands_data.get('commands', [])
        
        if cmd_index >= len(commands):
            await callback.answer("❌ Команда не найдена")
            return
        
        cmd = commands[cmd_index]
        
        confirm_text = (
            "⚠️ <b>Подтверждение удаления</b>\n\n"
            f"Вы действительно хотите удалить команду?\n\n"
            f"📝 <b>Название:</b> {cmd['name']}\n"
            f"🔤 <b>Триггер:</b> <code>{cmd['trigger']}</code>\n\n"
            f"<i>Это действие нельзя отменить!</i>"
        )
        
        await callback.message.edit_text(confirm_text, reply_markup=get_confirm_delete_keyboard(cmd_index))
    
    elif callback.data.startswith("cmd_delete_execute_"):
        cmd_index = int(callback.data.split("_")[3])
        commands_data = load_commands()
        commands = commands_data.get('commands', [])
        
        if cmd_index >= len(commands):
            await callback.answer("❌ Команда не найдена")
            return
        
        deleted_cmd = commands.pop(cmd_index)
        commands_data['commands'] = commands
        save_commands(commands_data)
        
        success_text = (
            "✅ <b>Команда удалена</b>\n\n"
            f"🗑️ Удалена команда: <b>{deleted_cmd['name']}</b>\n"
            f"🔤 Триггер: <code>{deleted_cmd['trigger']}</code>"
        )
        
        keyboard = [
            [
                InlineKeyboardButton(text="📋 К списку команд", callback_data="cmd_list"),
                InlineKeyboardButton(text="⬅️ В меню", callback_data="menu_commands")
            ]
        ]
        
        await callback.message.edit_text(success_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    
    await callback.answer()

@dp.callback_query(F.data == "cmd_refresh")
async def handle_cmd_refresh(callback: CallbackQuery):
    """Обновить список команд"""
    await handle_cmd_list(callback)
    await callback.answer("✅ Список обновлен")

@dp.callback_query(F.data == "cmd_cancel")
async def handle_cmd_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена создания команды"""
    await state.clear()
    await handle_menu_commands(callback)

@dp.callback_query(F.data == "cancel_sticker")
async def handle_cancel_sticker(callback: CallbackQuery, state: FSMContext):
    """Отмена установки стикера"""
    await state.clear()
    await handle_menu_main(callback)

# ==================== ОБРАБОТКА СООБЩЕНИЙ ДЛЯ FSM ====================

@dp.message(StickerStates.waiting_for_sticker, F.sticker)
async def process_sticker_input(message: types.Message, state: FSMContext):
    """Обработка полученного стикера"""
    if message.from_user.id != ADMIN_ID:
        return
    
    sticker = message.sticker
    sticker_id = sticker.file_id
    
    # Сохраняем данные
    data = load_sticker_data()
    data['sticker_id'] = sticker_id
    data['set_by'] = message.from_user.id
    data['set_at'] = datetime.now().isoformat()
    save_sticker_data(data)
    
    await state.clear()
    
    # Показываем стикер для подтверждения
    await message.answer_sticker(sticker_id)
    
    success_text = (
        "✅ <b>Стикер сохранен!</b>\n\n"
        f"<b>ID:</b> <code>{sticker_id[:50]}...</code>\n"
        f"<b>Emoji:</b> {sticker.emoji or 'нет'}\n\n"
        f"Теперь когда ты пишешь 'привет' в личных сообщениях,\n"
        f"я буду отправлять этот стикер от твоего лица!"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(text="📱 В меню", callback_data="menu_main"),
            InlineKeyboardButton(text="🎨 Другой стикер", callback_data="menu_set_sticker")
        ]
    ]
    
    await message.answer(success_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.message(CommandStates.waiting_for_command_name)
async def process_command_name(message: types.Message, state: FSMContext):
    """Обработка названия команды"""
    if message.from_user.id != ADMIN_ID:
        return
    
    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await message.answer("❌ Название должно быть от 2 до 50 символов")
        return
    
    await state.update_data(command_name=name)
    await state.set_state(CommandStates.waiting_for_command_trigger)
    
    trigger_text = (
        "➕ <b>Добавление новой команды</b>\n\n"
        "📝 <b>Шаг 2 из 3:</b> Введите триггер команды\n\n"
        "<i>Триггер должен начинаться с точки (.)</i>\n"
        "<i>Пример: .топ, .скидка, .контакты</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cmd_cancel"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_commands")
        ]
    ]
    
    await message.answer(trigger_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.message(CommandStates.waiting_for_command_trigger)
async def process_command_trigger(message: types.Message, state: FSMContext):
    """Обработка триггера команды"""
    if message.from_user.id != ADMIN_ID:
        return
    
    trigger = message.text.strip()
    
    # Проверяем формат триггера
    if not trigger.startswith('.'):
        await message.answer("❌ Триггер должен начинаться с точки (.)")
        return
    
    if len(trigger) < 2 or len(trigger) > 20:
        await message.answer("❌ Триггер должен быть от 2 до 20 символов")
        return
    
    # Проверяем, нет ли уже такой команды
    commands_data = load_commands()
    for cmd in commands_data.get('commands', []):
        if cmd['trigger'] == trigger:
            await message.answer(f"❌ Команда с триггером <code>{trigger}</code> уже существует")
            return
    
    await state.update_data(command_trigger=trigger)
    await state.set_state(CommandStates.waiting_for_command_response)
    
    response_text = (
        "➕ <b>Добавление новой команды</b>\n\n"
        "📝 <b>Шаг 3 из 3:</b> Введите ответ команды\n\n"
        "<i>Этот текст будет отправляться при использовании команды</i>\n"
        "<i>Можно использовать эмодзи и HTML-разметку</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cmd_cancel"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="cmd_add")
        ]
    ]
    
    await message.answer(response_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.message(CommandStates.waiting_for_command_response)
async def process_command_response(message: types.Message, state: FSMContext):
    """Обработка ответа команды"""
    if message.from_user.id != ADMIN_ID:
        return
    
    response = message.text.strip()
    if len(response) < 1 or len(response) > 1000:
        await message.answer("❌ Ответ должен быть от 1 до 1000 символов")
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    name = data.get('command_name')
    trigger = data.get('command_trigger')
    
    # Сохраняем команду
    commands_data = load_commands()
    if 'commands' not in commands_data:
        commands_data['commands'] = []
    
    new_command = {
        'name': name,
        'trigger': trigger,
        'response': response,
        'created_at': datetime.now().isoformat(),
        'created_by': message.from_user.id,
        'usage_count': 0
    }
    
    commands_data['commands'].append(new_command)
    save_commands(commands_data)
    
    await state.clear()
    
    success_text = (
        "🎉 <b>Команда успешно создана!</b>\n\n"
        f"📝 <b>Название:</b> {name}\n"
        f"🔤 <b>Триггер:</b> <code>{trigger}</code>\n"
        f"💬 <b>Ответ:</b>\n{response[:100]}...\n\n"
        f"<i>Теперь при написании {trigger} бот удалит команду и отправит ответ</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(text="➕ Еще команду", callback_data="cmd_add"),
            InlineKeyboardButton(text="📋 Список команд", callback_data="cmd_list")
        ],
        [
            InlineKeyboardButton(text="📱 В меню", callback_data="menu_main"),
            InlineKeyboardButton(text="🎯 Протестировать", callback_data=f"test_cmd_{trigger}")
        ]
    ]
    
    await message.answer(success_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.message(CommandStates.waiting_for_command_edit)
async def process_command_edit(message: types.Message, state: FSMContext):
    """Обработка редактирования команды"""
    if message.from_user.id != ADMIN_ID:
        return
    
    data = await state.get_data()
    edit_type = data.get('edit_type')
    cmd_index = data.get('cmd_index')
    new_value = message.text.strip()
    
    commands_data = load_commands()
    commands = commands_data.get('commands', [])
    
    if cmd_index >= len(commands):
        await message.answer("❌ Команда не найдена")
        await state.clear()
        return
    
    cmd = commands[cmd_index]
    
    # Валидация в зависимости от типа
    if edit_type == "name":
        if len(new_value) < 2 or len(new_value) > 50:
            await message.answer("❌ Название должно быть от 2 до 50 символов")
            return
        cmd['name'] = new_value
    
    elif edit_type == "trigger":
        if not new_value.startswith('.'):
            await message.answer("❌ Триггер должен начинаться с точки (.)")
            return
        
        # Проверяем, нет ли дубликата
        for i, existing_cmd in enumerate(commands):
            if existing_cmd['trigger'] == new_value and i != cmd_index:
                await message.answer(f"❌ Команда с триггером <code>{new_value}</code> уже существует")
                return
        
        cmd['trigger'] = new_value
    
    elif edit_type == "response":
        if len(new_value) < 1 or len(new_value) > 1000:
            await message.answer("❌ Ответ должен быть от 1 до 1000 символов")
            return
        cmd['response'] = new_value
    
    cmd['updated_at'] = datetime.now().isoformat()
    
    # Сохраняем изменения
    commands_data['commands'] = commands
    save_commands(commands_data)
    
    await state.clear()
    
    success_text = (
        "✅ <b>Команда обновлена!</b>\n\n"
        f"📝 <b>Название:</b> {cmd['name']}\n"
        f"🔤 <b>Триггер:</b> <code>{cmd['trigger']}</code>\n"
        f"💬 <b>Ответ:</b>\n{cmd['response'][:100]}..."
    )
    
    keyboard = [
        [
            InlineKeyboardButton(text="✏️ Еще редактировать", callback_data=f"cmd_view_{cmd_index}"),
            InlineKeyboardButton(text="📋 Список команд", callback_data="cmd_list")
        ],
        [
            InlineKeyboardButton(text="📱 В меню", callback_data="menu_main")
        ]
    ]
    
    await message.answer(success_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

# ==================== ОБРАБОТКА КОММАНД ПОЛЬЗОВАТЕЛЯ ====================

@dp.message(F.text)
async def handle_private_message(message: types.Message):
    """
    Обрабатывает ВСЕ текстовые сообщения от владельца
    1. Проверяет команды (начинающиеся с точки) и удаляет их
    2. Проверяет триггерные фразы для стикера
    """
    try:
        # Только сообщения ОТ владельца
        if message.from_user.id != ADMIN_ID:
            return
        
        # Только личные сообщения
        if message.chat.type not in ['private', 'sender']:
            return
        
        text = message.text.strip()
        if not text:
            return
        
        # 1. Проверяем команды пользователя (начинаются с точки)
        if text.startswith('.'):
            commands_data = load_commands()
            
            for cmd in commands_data.get('commands', []):
                if cmd['trigger'] == text.split()[0]:  # Проверяем только первое слово
                    # Увеличиваем счетчик использования
                    cmd['usage_count'] = cmd.get('usage_count', 0) + 1
                    save_commands(commands_data)
                    
                    # 🔥 УДАЛЯЕМ ИСХОДНОЕ СООБЩЕНИЕ С КОМАНДОЙ
                    try:
                        await message.delete()
                        logger.info(f"Удалено сообщение с командой: {cmd['trigger']}")
                    except Exception as delete_error:
                        logger.error(f"Не удалось удалить сообщение: {delete_error}")
                    
                    # Задержка для естественности
                    await asyncio.sleep(0.3)
                    
                    # Отправляем ответ команды
                    await message.answer(cmd['response'])
                    logger.info(f"Отправлена команда: {cmd['trigger']}")
                    return
        
        # 2. Проверяем триггерные фразы для стикера
        if is_trigger_message(text):
            logger.info(f"Триггер сработал: '{text}' в чате {message.chat.id}")
            
            # Задержка перед отправкой
            delay = random.uniform(0.5, 2.0)
            await asyncio.sleep(delay)
            
            # Отправляем стикер
            await send_sticker_as_user(message.chat.id)
            
            logger.info(f"Стикер отправлен в ответ на '{text}'")
    
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def is_trigger_message(text: str) -> bool:
    """Проверяет, содержит ли сообщение триггерную фразу"""
    if not text:
        return False
    
    text_lower = text.strip().lower()
    
    for phrase in TRIGGER_PHRASES:
        if phrase == text_lower:
            return True
        if phrase in text_lower and len(text_lower) < 50:
            return True
    
    return False

async def send_sticker_as_user(chat_id: int, business_connection_id: str = None) -> bool:
    """Отправляет стикер от имени пользователя"""
    data = load_sticker_data()
    sticker_id = data.get('sticker_id')
    
    if not sticker_id:
        logger.warning("ID стикера не установлен")
        return False
    
    try:
        if business_connection_id:
            await bot.send_sticker(
                chat_id=chat_id,
                sticker=sticker_id,
                business_connection_id=business_connection_id
            )
        else:
            await bot.send_sticker(
                chat_id=chat_id,
                sticker=sticker_id
            )
        
        # Обновляем статистику
        data['last_used'] = datetime.now().isoformat()
        data['total_sent'] = data.get('total_sent', 0) + 1
        save_sticker_data(data)
        
        logger.info(f"Стикер отправлен в чат {chat_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки стикера: {e}")
        return False

# ==================== BUSINESS API ПОДДЕРЖКА ====================

@dp.business_message(F.text)
async def handle_business_text(message: types.Message):
    """
    Обработка сообщений через Business API
    """
    try:
        if not hasattr(message, 'business_connection_id'):
            return
        
        if message.from_user.id != ADMIN_ID:
            return
        
        text = message.text.strip()
        if not text:
            return
        
        # 1. Проверяем команды
        if text.startswith('.'):
            commands_data = load_commands()
            
            for cmd in commands_data.get('commands', []):
                if cmd['trigger'] == text.split()[0]:
                    cmd['usage_count'] = cmd.get('usage_count', 0) + 1
                    save_commands(commands_data)
                    
                    # 🔥 УДАЛЯЕМ ИСХОДНОЕ СООБЩЕНИЕ (в бизнес-чате)
                    try:
                        await bot.delete_message(
                            chat_id=message.chat.id,
                            message_id=message.message_id
                        )
                        logger.info(f"Удалено бизнес-сообщение с командой: {cmd['trigger']}")
                    except Exception as delete_error:
                        logger.error(f"Не удалось удалить бизнес-сообщение: {delete_error}")
                    
                    await asyncio.sleep(0.3)
                    await message.answer(cmd['response'])
                    return
        
        # 2. Проверяем триггерные фразы
        if is_trigger_message(text):
            logger.info(f"Бизнес-триггер: '{text}' в чате {message.chat.id}")
            
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            data = load_sticker_data()
            sticker_id = data.get('sticker_id')
            
            if sticker_id:
                await bot.send_sticker(
                    chat_id=message.chat.id,
                    sticker=sticker_id,
                    business_connection_id=message.business_connection_id
                )
                
                data['total_sent'] = data.get('total_sent', 0) + 1
                data['last_used'] = datetime.now().isoformat()
                save_sticker_data(data)
                
                logger.info(f"Бизнес-стикер отправлен")
    
    except Exception as e:
        logger.error(f"Ошибка бизнес-обработки: {e}")

# ==================== ЗАПУСК БОТА ====================

async def main():
    """Запуск бота"""
    print("=" * 50)
    print("🤖 УЛУЧШЕННЫЙ СТИКЕР-БОТ ДЛЯ TELEGRAM")
    print("✨ С инлайн-кнопками и системой команд")
    print("🔥 Команды автоматически удаляются при использовании")
    print(f"👤 Владелец: {ADMIN_ID}")
    print("=" * 50)
    
    # Загружаем данные
    sticker_data = load_sticker_data()
    commands_data = load_commands()
    
    if sticker_data.get('sticker_id'):
        print(f"✅ Стикер установлен (отправлено: {sticker_data.get('total_sent', 0)})")
    else:
        print("⚠️ Стикер не установлен. Используй меню для настройки")
    
    print(f"📝 Загружено команд: {len(commands_data.get('commands', []))}")
    print("🔄 Бот запущен и слушает сообщения...")
    print("🔥 Команды (.топ) будут автоматически удаляться")
    print("=" * 50)
    
    # Устанавливаем команды бота
    await bot.set_my_commands([
        types.BotCommand(command="start", description="Запустить бота"),
        types.BotCommand(command="menu", description="Главное меню"),
        types.BotCommand(command="help", description="Помощь")
    ])
    
    # Запускаем polling
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
