from telethon import TelegramClient, events
import os
from urllib.parse import urlparse

api_id = 8000395560
api_hash = '3c57df8805ab5de5a23a032ed39b9af9'
bot_token = '7971014285:AAGe6IbdI7_dLHsn3UdGBER-wZRKK-buSys'

client = TelegramClient('bot_session', api_id, api_hash).start(bot_token=bot_token)

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    await event.reply("Отправь мне ссылку на сообщение в формате 'https://t.me/username/123', и я скачаю его для тебя.")

@client.on(events.NewMessage)
async def url_handler(event):
    message_text = event.message.message
    parsed_url = urlparse(message_text)

    if 't.me' not in parsed_url.netloc:
        await event.reply("Это не похоже на ссылку Telegram.")
        return

    try:
        parts = parsed_url.path.strip('/').split('/')
        chat_username = parts[0]
        message_id = int(parts[1])

        target_chat = await client.get_entity(chat_username)
        target_message = await client.get_messages(target_chat, ids=message_id)

        if target_message:
            await event.reply("Скачиваю...")

            download_path = f"./downloads/{message_id}/"
            os.makedirs(download_path, exist_ok=True)

            file_path = await target_message.download_media(file=download_path)

            if file_path:
                await client.send_file(event.chat_id, file_path, caption="Вот твой файл.")
            else:
                await event.reply("В этом сообщении нет медиафайлов.")
        else:
            await event.reply("Не удалось найти сообщение.")

    except Exception as e:
        await event.reply(f"Ошибка: {str(e)}")

client.start()
client.run_until_disconnected()
