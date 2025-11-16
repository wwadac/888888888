import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon import functions, types
import sqlite3
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# КОНФИГУРАЦИЯ - ЗАПОЛНИТЕ СВОИ ДАННЫЕ!
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
    conn.commit()
    conn.close()

init_db()

# Хранилище состояний и данных авторизации
user_states = {}
auth_data = {}

# Главное меню
@bot.on_message(filters.command("start"))
async def start_command(client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить аккаунт", callback_data="add_account")],
        [InlineKeyboardButton("📋 Мои аккаунты", callback_data="my_accounts")],
        [InlineKeyboardButton("⚙️ Управление аккаунтом", callback_data="manage_account")]
    ])
    
    await message.reply_text(
        "👋 **Добро пожаловать в менеджер аккаунтов Telegram!**\n\n"
        "Вы можете:\n"
        "• Добавлять аккаунты через телефон\n"
        "• Управлять профилем\n"
        "• Изменять username, био и т.д.\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

# Добавление аккаунта
@bot.on_callback_query(filters.regex("add_account"))
async def add_account_callback(client, callback_query):
    await callback_query.message.edit_text(
        "📱 **Добавление аккаунта**\n\n"
        "Пожалуйста, введите номер телефона в международном формате:\n"
        "Пример: +79123456789"
    )
    
    user_states[callback_query.from_user.id] = "waiting_phone"

# Обработка ввода номера телефона
@bot.on_message(filters.private & filters.text & ~filters.command("start"))
async def handle_phone_input(client, message: Message):
    user_id = message.from_user.id
    
    if user_states.get(user_id) == "waiting_phone":
        phone = message.text.strip()
        
        if not re.match(r'^\+\d{10,15}$', phone):
            await message.reply_text("❌ Неверный формат номера. Используйте международный формат (+79123456789)")
            return
        
        user_states[user_id] = f"waiting_code_{phone}"
        
        await message.reply_text(
            f"📞 Номер: {phone}\n\n"
            "Запускаю авторизацию...\n"
            "Вам придет код подтверждения. Пришлите его сюда в формате: 12345"
        )
        
        await start_authorization(user_id, phone, message)
    
    elif "waiting_code_" in user_states.get(user_id, ""):
        phone = user_states[user_id].split("_")[2]
        code = message.text.strip()
        
        try:
            await complete_authorization(user_id, phone, code, message)
        except Exception as e:
            await message.reply_text(f"❌ Ошибка: {str(e)}")
    
    elif "waiting_2fa_" in user_states.get(user_id, ""):
        phone = user_states[user_id].split("_")[2]
        password = message.text.strip()
        
        try:
            await complete_2fa(user_id, phone, password, message)
        except Exception as e:
            await message.reply_text(f"❌ Ошибка 2FA: {str(e)}")

# Функция авторизации
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

# Завершение авторизации
async def complete_authorization(user_id, phone, code, message):
    try:
        data = auth_data.get(user_id)
        if not data:
            await message.reply_text("❌ Сессия авторизации устарела. Начните заново.")
            return
        
        client = data['client']
        
        try:
            # Пытаемся войти с кодом
            await client.sign_in(
                phone=phone,
                code=code,
                phone_code_hash=data['phone_code_hash']
            )
        except Exception as e:
            # Если требуется 2FA пароль
            if "2FA" in str(e) or "PASSWORD" in str(e):
                user_states[user_id] = f"waiting_2fa_{phone}"
                await message.reply_text(
                    "🔐 **Требуется двухфакторная аутентификация**\n\n"
                    "Введите ваш 2FA пароль:"
                )
                return
            else:
                raise e
        
        # Если успешно вошли без 2FA
        await save_session_and_info(user_id, client, phone, message)
        
    except Exception as e:
        await message.reply_text(f"❌ Ошибка при авторизации: {str(e)}")

# Завершение 2FA аутентификации
async def complete_2fa(user_id, phone, password, message):
    try:
        data = auth_data.get(user_id)
        if not data:
            await message.reply_text("❌ Сессия авторизации устарела. Начните заново.")
            return
        
        client = data['client']
        
        # Входим с 2FA паролем
        await client.sign_in(
            phone=phone,
            password=password
        )
        
        await save_session_and_info(user_id, client, phone, message)
        
    except Exception as e:
        await message.reply_text(f"❌ Ошибка при 2FA аутентификации: {str(e)}")

# Сохранение сессии и информации
async def save_session_and_info(user_id, client, phone, message):
    try:
        session_string = client.session.save()
        
        # Сохраняем в базу данных
        conn = sqlite3.connect('sessions.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO accounts (user_id, session_string, phone) VALUES (?, ?, ?)",
            (user_id, session_string, phone)
        )
        conn.commit()
        conn.close()
        
        # Получаем информацию об аккаунте
        me = await client.get_me()
        
        await message.reply_text(
            f"✅ **Аккаунт успешно добавлен!**\n\n"
            f"👤 Имя: {me.first_name or ''}\n"
            f"📱 Телефон: {phone}\n"
            f"🔗 Username: @{me.username or 'нет'}\n"
            f"🆔 ID: {me.id}\n"
            f"🔐 2FA: {'Да' if me.premium else 'Нет'}"
        )
        
        await client.disconnect()
        
        # Очищаем данные
        if user_id in auth_data:
            del auth_data[user_id]
        if user_id in user_states:
            del user_states[user_id]
            
    except Exception as e:
        await message.reply_text(f"❌ Ошибка при сохранении сессии: {str(e)}")

# Показать мои аккаунты
@bot.on_callback_query(filters.regex("my_accounts"))
async def show_accounts_callback(client, callback_query):
    user_id = callback_query.from_user.id
    
    conn = sqlite3.connect('sessions.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, phone FROM accounts WHERE user_id = ?", (user_id,))
    accounts = cursor.fetchall()
    conn.close()
    
    if not accounts:
        await callback_query.message.edit_text("❌ У вас нет добавленных аккаунтов.")
        return
    
    text = "📋 **Ваши аккаунты:**\n\n"
    keyboard = []
    
    for account_id, phone in accounts:
        text += f"📱 {phone} (ID: {account_id})\n"
        keyboard.append([InlineKeyboardButton(f"👤 {phone}", callback_data=f"manage_{account_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# Управление аккаунтом
@bot.on_callback_query(filters.regex(r"manage_\d+"))
async def manage_account_callback(client, callback_query):
    account_id = int(callback_query.data.split("_")[1])
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Изменить имя", callback_data=f"change_name_{account_id}")],
        [InlineKeyboardButton("🔗 Изменить username", callback_data=f"change_username_{account_id}")],
        [InlineKeyboardButton("📝 Изменить био", callback_data=f"change_bio_{account_id}")],
        [InlineKeyboardButton("📊 Информация", callback_data=f"account_info_{account_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="my_accounts")]
    ])
    
    await callback_query.message.edit_text(
        "⚙️ **Управление аккаунтом**\n\nВыберите действие:",
        reply_markup=keyboard
    )

# Получение клиента по ID аккаунта
async def get_client_by_account_id(account_id, user_id):
    try:
        conn = sqlite3.connect('sessions.db')
        cursor = conn.cursor()
        cursor.execute("SELECT session_string FROM accounts WHERE id = ? AND user_id = ?", (account_id, user_id))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        session_string = result[0]
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        # Проверяем валидность сессии
        me = await client.get_me()
        return client
    except Exception as e:
        logger.error(f"Error creating client: {e}")
        return None

# Изменение имени
@bot.on_callback_query(filters.regex(r"change_name_\d+"))
async def change_name_callback(client, callback_query):
    account_id = int(callback_query.data.split("_")[2])
    user_states[callback_query.from_user.id] = f"change_first_name_{account_id}"
    
    await callback_query.message.edit_text(
        "✏️ **Изменение имени**\n\n"
        "Введите новое имя и фамилию через пробел:\n"
        "Пример: Иван Иванов"
    )

# Обработка изменения имени
@bot.on_message(filters.private & filters.text & ~filters.command("start"))
async def handle_name_change(client, message: Message):
    user_id = message.from_user.id
    state = user_states.get(user_id, "")
    
    if state.startswith("change_first_name_"):
        account_id = int(state.split("_")[3])
        names = message.text.strip().split(" ", 1)
        
        if len(names) < 1:
            await message.reply_text("❌ Пожалуйста, введите имя")
            return
        
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ""
        
        client_instance = await get_client_by_account_id(account_id, user_id)
        if not client_instance:
            await message.reply_text("❌ Ошибка доступа к аккаунту")
            return
        
        try:
            await client_instance(functions.account.UpdateProfileRequest(
                first_name=first_name,
                last_name=last_name
            ))
            
            await message.reply_text("✅ Имя успешно изменено!")
            await client_instance.disconnect()
            
        except Exception as e:
            await message.reply_text(f"❌ Ошибка при изменении имени: {str(e)}")
        
        if user_id in user_states:
            del user_states[user_id]

# Информация об аккаунте
@bot.on_callback_query(filters.regex(r"account_info_\d+"))
async def account_info_callback(client, callback_query):
    account_id = int(callback_query.data.split("_")[2])
    user_id = callback_query.from_user.id
    
    client_instance = await get_client_by_account_id(account_id, user_id)
    if not client_instance:
        await callback_query.message.edit_text("❌ Ошибка доступа к аккаунту")
        return
    
    try:
        me = await client_instance.get_me()
        
        info_text = (
            f"📊 **Информация об аккаунте**\n\n"
            f"👤 ID: {me.id}\n"
            f"📱 Телефон: {me.phone or 'скрыт'}\n"
            f"🆔 Username: @{me.username or 'нет'}\n"
            f"📛 Имя: {me.first_name or ''}\n"
            f"📚 Фамилия: {me.last_name or ''}\n"
            f"🤖 Бот: {'Да' if me.bot else 'Нет'}\n"
            f"✅ Премиум: {'Да' if me.premium else 'Нет'}\n"
            f"🔐 2FA: {'Включена' if me.premium else 'Выключена'}"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data=f"manage_{account_id}")]
        ])
        
        await callback_query.message.edit_text(info_text, reply_markup=keyboard)
        await client_instance.disconnect()
        
    except Exception as e:
        await callback_query.message.edit_text(f"❌ Ошибка при получении информации: {str(e)}")

# Назад в главное меню
@bot.on_callback_query(filters.regex("back_to_main"))
async def back_to_main_callback(client, callback_query):
    await start_command(client, callback_query.message)

# Запуск бота
if __name__ == "__main__":
    print("🤖 Бот запускается...")
    print("✅ Pyrogram и Telethon инициализированы")
    print("📱 Бот готов к работе!")
    bot.run()
