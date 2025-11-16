import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon import functions, types
import sqlite3
import re
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# КОНФИГУРАЦИЯ
API_ID = "29385016  "  # Получите на my.telegram.org
API_HASH = "3c57df8805ab5de5a23a032ed39b9af9"  # Получите на my.telegram.org
BOT_TOKEN = "8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk"  # Получите у @BotFather

# Инициализация бота
bot = Client("account_manager", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# База данных
def init_db():
    conn = sqlite3.connect('sessions.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_string TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS login_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_user_id INTEGER,
            requester_user_id INTEGER,
            phone TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Хранилище состояний
user_states = {}
auth_data = {}
pending_requests = {}

# Главное меню
@bot.on_message(filters.command("start"))
async def start_command(client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 Запросить вход в аккаунт", callback_data="request_login")],
        [InlineKeyboardButton("📋 Мои аккаунты", callback_data="my_accounts")],
        [InlineKeyboardButton("📨 Запросы на вход", callback_data="view_requests")]
    ])
    
    await message.reply_text(
        "👋 **Система управления аккаунтами с подтверждением**\n\n"
        "🔐 **Безопасный вход с подтверждением**\n"
        "• Запросите доступ к аккаунту\n"
        "• Владелец получит запрос\n"
        "• Только после подтверждения - вход\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

# Запрос на вход в аккаунт
@bot.on_callback_query(filters.regex("request_login"))
async def request_login_callback(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "🔐 **Запрос доступа к аккаунту**\n\n"
        "Введите номер телефона аккаунта в международном формате:\n"
        "Пример: +79123456789\n\n"
        "⚠️ Владелец аккаунта получит запрос и должен будет его подтвердить!"
    )
    user_states[callback_query.from_user.id] = "request_phone_input"

# Обработка ввода номера для запроса
@bot.on_message(filters.private & filters.text & ~filters.command("start"))
async def handle_request_phone(client, message: Message):
    user_id = message.from_user.id
    
    if user_states.get(user_id) == "request_phone_input":
        phone = message.text.strip()
        
        if not re.match(r'^\+\d{10,15}$', phone):
            await message.reply_text("❌ Неверный формат номера. Используйте международный формат (+79123456789)")
            return
        
        # Ищем владельца аккаунта в базе
        conn = sqlite3.connect('sessions.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM accounts WHERE phone = ?", (phone,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            await message.reply_text("❌ Аккаунт с таким номером не найден в системе или не добавлен в бота")
            user_states.pop(user_id, None)
            return
        
        target_user_id = result[0]
        
        # Сохраняем запрос в базу
        conn = sqlite3.connect('sessions.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO login_requests (target_user_id, requester_user_id, phone, status) VALUES (?, ?, ?, ?)",
            (target_user_id, user_id, phone, 'pending')
        )
        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Отправляем запрос владельцу аккаунта
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Разрешить вход", callback_data=f"approve_{request_id}")],
            [InlineKeyboardButton("❌ Запретить вход", callback_data=f"reject_{request_id}")]
        ])
        
        try:
            await client.send_message(
                target_user_id,
                f"🔐 **Запрос на вход в аккаунт**\n\n"
                f"📱 Номер: `{phone}`\n"
                f"👤 Пользователь: {message.from_user.mention}\n"
                f"🆔 ID: `{user_id}`\n"
                f"⏰ Время: {datetime.now().strftime('%H:%M %d.%m.%Y')}\n\n"
                f"Разрешить вход?",
                reply_markup=keyboard
            )
            
            await message.reply_text(
                f"✅ **Запрос отправлен!**\n\n"
                f"📱 Номер: `{phone}`\n"
                f"⏳ Ожидайте подтверждения от владельца аккаунта...\n\n"
                f"Вы получите уведомление, когда запрос будет обработан."
            )
            
        except Exception as e:
            await message.reply_text("❌ Не удалось отправить запрос владельцу аккаунта")
        
        user_states.pop(user_id, None)

# Обработка подтверждения/отклонения запроса
@bot.on_callback_query(filters.regex(r"^(approve|reject)_\d+"))
async def handle_request_decision(client, callback_query: CallbackQuery):
    action, request_id = callback_query.data.split("_")
    request_id = int(request_id)
    
    # Получаем информацию о запросе
    conn = sqlite3.connect('sessions.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT target_user_id, requester_user_id, phone FROM login_requests WHERE id = ? AND status = 'pending'",
        (request_id,)
    )
    result = cursor.fetchone()
    
    if not result:
        await callback_query.answer("Запрос уже обработан", show_alert=True)
        return
    
    target_user_id, requester_user_id, phone = result
    
    if action == "approve":
        # Обновляем статус запроса
        cursor.execute("UPDATE login_requests SET status = 'approved' WHERE id = ?", (request_id,))
        conn.commit()
        
        # Уведомляем владельца
        await callback_query.message.edit_text(
            "✅ **Доступ разрешен!**\n\n"
            f"Пользователь может теперь войти в аккаунт {phone}"
        )
        
        # Уведомляем запрашивающего
        try:
            await client.send_message(
                requester_user_id,
                f"✅ **Доступ разрешен!**\n\n"
                f"Владелец аккаунта {phone} разрешил вам вход.\n\n"
                f"Теперь вы можете начать процесс авторизации. Нажмите кнопку ниже:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔐 Начать авторизацию", callback_data=f"start_auth_{phone}")
                ]])
            )
        except Exception as e:
            logger.error(f"Error notifying requester: {e}")
    
    else:  # reject
        # Обновляем статус запроса
        cursor.execute("UPDATE login_requests SET status = 'rejected' WHERE id = ?", (request_id,))
        conn.commit()
        
        # Уведомляем владельца
        await callback_query.message.edit_text(
            "❌ **Доступ запрещен!**\n\n"
            f"Запрос на вход в аккаунт {phone} отклонен"
        )
        
        # Уведомляем запрашивающего
        try:
            await client.send_message(
                requester_user_id,
                f"❌ **Доступ запрещен!**\n\n"
                f"Владелец аккаунта {phone} отклонил ваш запрос на вход."
            )
        except Exception as e:
            logger.error(f"Error notifying requester: {e}")
    
    conn.close()

# Начало авторизации после подтверждения
@bot.on_callback_query(filters.regex(r"start_auth_\+\d+"))
async def start_auth_after_approval(client, callback_query: CallbackQuery):
    phone = callback_query.data.replace("start_auth_", "")
    user_id = callback_query.from_user.id
    
    # Проверяем, что запрос действительно подтвержден
    conn = sqlite3.connect('sessions.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM login_requests WHERE requester_user_id = ? AND phone = ? AND status = 'approved'",
        (user_id, phone)
    )
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        await callback_query.answer("Запрос не подтвержден или устарел", show_alert=True)
        return
    
    # Начинаем процесс авторизации
    user_states[user_id] = f"waiting_code_{phone}"
    
    await callback_query.message.edit_text(
        f"🔐 **Начало авторизации**\n\n"
        f"📱 Номер: {phone}\n\n"
        f"Запускаю процесс входа...\n"
        f"Вам придет код подтверждения. Пришлите его сюда в формате: 12345"
    )
    
    await start_authorization(user_id, phone, callback_query.message)

# Функция авторизации (остается такой же как в предыдущем коде)
async def start_authorization(user_id, phone, message):
    try:
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        
        sent_code = await client.send_code_request(phone)
        
        auth_data[user_id] = {
            'client': client,
            'phone': phone,
            'phone_code_hash': sent_code.phone_code_hash
        }
        
        await message.reply_text("✅ Код отправлен! Проверьте Telegram и введите код:")
        
    except Exception as e:
        await message.reply_text(f"❌ Ошибка при отправке кода: {str(e)}")

# Просмотр запросов
@bot.on_callback_query(filters.regex("view_requests"))
async def view_requests_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    
    conn = sqlite3.connect('sessions.db')
    cursor = conn.cursor()
    
    # Запросы, которые отправил пользователь
    cursor.execute('''
        SELECT lr.id, lr.phone, lr.status, lr.created_at, u.first_name 
        FROM login_requests lr 
        LEFT JOIN users u ON lr.target_user_id = u.id 
        WHERE lr.requester_user_id = ?
        ORDER BY lr.created_at DESC LIMIT 10
    ''', (user_id,))
    my_requests = cursor.fetchall()
    
    # Запросы, которые пришли пользователю
    cursor.execute('''
        SELECT lr.id, lr.phone, lr.status, lr.created_at, u.first_name 
        FROM login_requests lr 
        LEFT JOIN users u ON lr.requester_user_id = u.id 
        WHERE lr.target_user_id = ? AND lr.status = 'pending'
        ORDER BY lr.created_at DESC LIMIT 10
    ''', (user_id,))
    incoming_requests = cursor.fetchall()
    
    conn.close()
    
    text = "📨 **Запросы на вход**\n\n"
    
    if incoming_requests:
        text += "🔄 **Входящие запросы:**\n"
        for req in incoming_requests:
            req_id, phone, status, created_at, first_name = req
            text += f"📱 {phone} - ⏳ Ожидает\n"
    
    if my_requests:
        text += "\n📤 **Мои запросы:**\n"
        for req in my_requests:
            req_id, phone, status, created_at, first_name = req
            status_icon = "✅" if status == "approved" else "❌" if status == "rejected" else "⏳"
            text += f"📱 {phone} - {status_icon} {status}\n"
    
    if not incoming_requests and not my_requests:
        text += "📭 Нет активных запросов"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)

# Назад в главное меню
@bot.on_callback_query(filters.regex("back_to_main"))
async def back_to_main_callback(client, callback_query: CallbackQuery):
    await start_command(client, callback_query.message)

# Запуск бота
if __name__ == "__main__":
    print("🔐 Бот с системой подтверждения запускается...")
    bot.run()
