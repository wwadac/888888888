import asyncio
import logging
import os
import sqlite3
import json
from pyrogram import Client, filters, types
from telethon import TelegramClient
from telethon.sessions import StringSession

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация из переменных окружения bothost.ru
BOT_TOKEN = os.getenv("BOT_TOKEN", "8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk")
API_ID = os.getenv("API_ID", "29385016  ")  # Замените на ваш API_ID
API_HASH = os.getenv("API_HASH", "3c57df8805ab5de5a23a032ed39b9af9")  # Замените на ваш API_HASH
ADMIN_ID = int(os.getenv("USER_ID_RAW", "6893832048"))  # Ваш USER_ID
DOMAIN = os.getenv("DOMAIN", "bot_1763278432_6473_111ggg111.bothost.ru")
PORT = int(os.getenv("PORT", "3000"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://bot_1763278432_6473_111ggg111.bothost.ru/webhook")

# Инициализация бота Pyrogram
bot = Client(
    name="account_manager",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=3,  # Оптимизация для бесплатного тарифа
    sleep_threshold=60
)

# Инициализация базы данных
def init_db():
    try:
        conn = sqlite3.connect('/tmp/sessions.db')  # Используем /tmp для bothost.ru
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE,
                session_string TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT,
                client_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")

# Получение информации о пользователе
def get_user_info():
    return {
        "user_id": os.getenv("USER_ID_RAW"),
        "domain": DOMAIN,
        "plan": os.getenv("BOTHOST_USER_PLAN", "free"),
        "max_bots": int(os.getenv("BOTHOST_MAX_BOTS", 3)),
        "max_messages": int(os.getenv("BOTHOST_MAX_MESSAGES_PER_DAY", 1000))
    }

# Главное меню
async def get_main_keyboard():
    return types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("➕ Добавить аккаунт", callback_data="add_account")],
        [types.InlineKeyboardButton("📋 Мои аккаунты", callback_data="list_accounts")],
        [types.InlineKeyboardButton("📤 Отправить сообщение", callback_data="send_message")],
        [types.InlineKeyboardButton("🔄 Статус", callback_data="status")]
    ])

# Команда /start
@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    user_info = get_user_info()
    
    if message.from_user.id != ADMIN_ID:
        await message.reply("⛔ Доступ запрещен!")
        return
    
    welcome_text = f"""
🤖 **Account Manager Bot**
📍 *Размещено на bothost.ru*

👤 **Пользователь:** `{user_info['user_id']}`
📊 **Тариф:** `{user_info['plan']}`
🤖 **Доступно ботов:** `{user_info['max_bots']}`
💬 **Лимит сообщений:** `{user_info['max_messages']}/день`

Выберите действие:
    """
    
    await message.reply(welcome_text, reply_markup=await get_main_keyboard())

# Добавление аккаунта
@bot.on_callback_query(filters.regex("add_account"))
async def add_account_callback(client, callback_query):
    user_info = get_user_info()
    
    # Проверяем лимит ботов
    conn = sqlite3.connect('/tmp/sessions.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sessions WHERE is_active = 1")
    active_accounts = cursor.fetchone()[0]
    conn.close()
    
    if active_accounts >= user_info['max_bots']:
        await callback_query.answer(f"❌ Лимит ботов достигнут! Максимум: {user_info['max_bots']}", show_alert=True)
        return
    
    await callback_query.message.edit_text(
        "📱 **Добавление аккаунта**\n\n"
        "Введите номер телефона в международном формате:\n"
        "Пример: `+79123456789`\n\n"
        f"📍 *bothost.ru | {user_info['plan']} план*"
    )
    await callback_query.answer()

# Обработка номера телефона
@bot.on_message(filters.private & filters.text & filters.regex(r'^\+\d{11,12}$'))
async def handle_phone_number(client, message):
    if message.from_user.id != ADMIN_ID:
        return
    
    phone = message.text
    
    try:
        # Проверяем существующую сессию
        conn = sqlite3.connect('/tmp/sessions.db')
        cursor = conn.cursor()
        cursor.execute("SELECT session_string FROM sessions WHERE phone = ? AND is_active = 1", (phone,))
        existing_session = cursor.fetchone()
        
        if existing_session:
            await message.reply("✅ Аккаунт уже добавлен и активен!")
            conn.close()
            return
        
        conn.close()
        
        await message.reply(f"🔐 Отправка кода на номер: `{phone}`\n\n⏳ Ожидайте код подтверждения...")
        
        # Создаем клиент Telethon для авторизации
        client_tg = TelegramClient(StringSession(), API_ID, API_HASH)
        await client_tg.connect()
        
        # Отправляем код
        sent_code = await client_tg.send_code_request(phone)
        
        # Сохраняем данные для верификации
        conn = sqlite3.connect('/tmp/sessions.db')
        cursor = conn.cursor()
        client_data = {
            'phone': phone,
            'phone_code_hash': sent_code.phone_code_hash
        }
        cursor.execute(
            "INSERT OR REPLACE INTO auth_requests (phone, client_data) VALUES (?, ?)",
            (phone, json.dumps(client_data))
        )
        conn.commit()
        conn.close()
        
        await message.reply(
            f"📲 **Код отправлен на {phone}**\n\n"
            "Введите полученный код в формате:\n"
            "`12345`\n\n"
            "⏳ *Ожидание кода...*"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при отправке кода: {e}")
        await message.reply(f"❌ Ошибка: {str(e)}")

# Обработка кода подтверждения
@bot.on_message(filters.private & filters.text & filters.regex(r'^\d{5}$'))
async def handle_verification_code(client, message):
    if message.from_user.id != ADMIN_ID:
        return
    
    code = message.text
    
    try:
        conn = sqlite3.connect('/tmp/sessions.db')
        cursor = conn.cursor()
        cursor.execute("SELECT phone, client_data FROM auth_requests ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        
        if not result:
            await message.reply("❌ Сначала введите номер телефона!")
            conn.close()
            return
        
        phone, client_data_str = result
        client_data = json.loads(client_data_str)
        
        # Завершаем авторизацию
        client_tg = TelegramClient(StringSession(), API_ID, API_HASH)
        await client_tg.connect()
        
        await client_tg.sign_in(
            phone=phone,
            code=code,
            phone_code_hash=client_data['phone_code_hash']
        )
        
        # Получаем строку сессии
        session_string = client_tg.session.save()
        
        # Сохраняем сессию в базу
        cursor.execute(
            "INSERT OR REPLACE INTO sessions (phone, session_string, is_active) VALUES (?, ?, 1)",
            (phone, session_string)
        )
        
        # Очищаем временные данные
        cursor.execute("DELETE FROM auth_requests WHERE phone = ?", (phone,))
        conn.commit()
        conn.close()
        
        await client_tg.disconnect()
        
        await message.reply(
            f"✅ **Аккаунт успешно добавлен!**\n\n"
            f"📱 Номер: `{phone}`\n"
            f"🔐 Сессия сохранена\n"
            f"📍 *bothost.ru*"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при верификации: {e}")
        await message.reply(f"❌ Ошибка верификации: {str(e)}")

# Список аккаунтов
@bot.on_callback_query(filters.regex("list_accounts"))
async def list_accounts_callback(client, callback_query):
    try:
        conn = sqlite3.connect('/tmp/sessions.db')
        cursor = conn.cursor()
        cursor.execute("SELECT phone, created_at FROM sessions WHERE is_active = 1")
        accounts = cursor.fetchall()
        conn.close()
        
        user_info = get_user_info()
        
        if not accounts:
            await callback_query.message.edit_text(
                "📭 Нет добавленных аккаунтов\n\n"
                f"📍 *bothost.ru | {user_info['plan']} план*"
            )
            return
        
        accounts_text = "📋 **Мои аккаунты:**\n\n"
        for i, (phone, created_at) in enumerate(accounts, 1):
            accounts_text += f"{i}. `{phone}`\n   🕒 {created_at[:10]}\n"
        
        accounts_text += f"\n📍 *Всего: {len(accounts)}/{user_info['max_bots']} аккаунтов*"
        
        keyboard = types.InlineKeyboardMarkup([
            [types.InlineKeyboardButton("🔄 Обновить", callback_data="list_accounts")],
            [types.InlineKeyboardButton("📊 Статус", callback_data="status")],
            [types.InlineKeyboardButton("🏠 Главная", callback_data="main_menu")]
        ])
        
        await callback_query.message.edit_text(accounts_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка аккаунтов: {e}")
        await callback_query.answer("❌ Ошибка при загрузке списка", show_alert=True)

# Статус системы
@bot.on_callback_query(filters.regex("status"))
async def status_callback(client, callback_query):
    user_info = get_user_info()
    
    conn = sqlite3.connect('/tmp/sessions.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sessions WHERE is_active = 1")
    active_accounts = cursor.fetchone()[0]
    conn.close()
    
    status_text = f"""
📊 **Статус системы**
📍 *bothost.ru*

👤 Пользователь: `{user_info['user_id']}`
📋 Тариф: `{user_info['plan']}`
🤖 Аккаунты: `{active_accounts}/{user_info['max_bots']}`
💬 Лимит сообщений: `{user_info['max_messages']}/день`
🌐 Домен: `{DOMAIN}`

✅ **Бот активен и работает**
    """
    
    keyboard = types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("🔄 Обновить", callback_data="status")],
        [types.InlineKeyboardButton("🏠 Главная", callback_data="main_menu")]
    ])
    
    await callback_query.message.edit_text(status_text, reply_markup=keyboard)
    await callback_query.answer()

# Возврат в главное меню
@bot.on_callback_query(filters.regex("main_menu"))
async def main_menu_callback(client, callback_query):
    user_info = get_user_info()
    
    welcome_text = f"""
🤖 **Account Manager Bot**
📍 *Размещено на bothost.ru*

👤 **Пользователь:** `{user_info['user_id']}`
📊 **Тариф:** `{user_info['plan']}`
🤖 **Доступно ботов:** `{user_info['max_bots']}`
💬 **Лимит сообщений:** `{user_info['max_messages']}/день`

Выберите действие:
    """
    
    await callback_query.message.edit_text(welcome_text, reply_markup=await get_main_keyboard())
    await callback_query.answer()

# Обработка неизвестных сообщений
@bot.on_message(filters.private & filters.text)
async def handle_unknown_message(client, message):
    if message.from_user.id != ADMIN_ID:
        return
    
    await message.reply(
        "🤔 Неизвестная команда\n\n"
        "Используйте кнопки меню или команду /start",
        reply_markup=await get_main_keyboard()
    )

# Запуск бота
async def main():
    logger.info("Инициализация бота...")
    
    # Инициализация БД
    init_db()
    
    # Запуск бота
    await bot.start()
    
    # Получение информации о боте
    me = await bot.get_me()
    user_info = get_user_info()
    
    logger.info(f"Бот @{me.username} запущен!")
    logger.info(f"Пользователь: {user_info['user_id']}")
    logger.info(f"Тариф: {user_info['plan']}")
    logger.info(f"Домен: {DOMAIN}")
    
    # Бесконечное ожидание
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
