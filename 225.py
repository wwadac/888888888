import asyncio
from telethon import TelegramClient, events
import re
import os

# НАСТРОЙКИ
API_ID = 29385016 # Получить на my.telegram.org
API_HASH = '3c57df8805ab5de5a23a032ed39b9af9'  # Получить на my.telegram.org
BOT_TOKEN = '7971014285:AAGe6IbdI7_dLHsn3UdGBER-wZRKK-buSys'  # Получить у @BotFather
USER_SESSION = 'user_account.session'  # Файл сессии пользователя

async def download_media(chat_identifier, message_id):
    user_client = None
    try:
        # Создаем клиента внутри функции
        user_client = TelegramClient(USER_SESSION, API_ID, API_HASH)
        await user_client.start()
        
        # Получаем сообщение
        message = await user_client.get_messages(chat_identifier, ids=message_id)
        
        if not message or not message.media:
            return None, "Сообщение или медиа не найдено"
        
        # Создаем папку для загрузок
        os.makedirs("downloads", exist_ok=True)
        
        # Скачиваем медиа
        file_path = await message.download_media(file="downloads/")
        return file_path, "Успешно"
        
    except Exception as e:
        return None, f"Ошибка: {str(e)}"
    finally:
        if user_client:
            await user_client.disconnect()

async def main():
    # Создаем бот клиент
    bot_client = TelegramClient('bot', API_ID, API_HASH)
    
    @bot_client.on(events.NewMessage(pattern='/start'))
    async def start(event):
        await event.reply('''Отправь ссылку на сообщение в формате:
https://t.me/username/123
https://t.me/c/chat_id/123''')

    @bot_client.on(events.NewMessage)
    async def handle_message(event):
        text = event.text
        
        if not text.startswith('https://t.me/'):
            return
            
        # Парсим ссылку
        pattern = r'https://t\.me/(c/(\d+)|(\w+))/(\d+)'
        match = re.search(pattern, text)
        
        if not match:
            await event.reply("Неверный формат ссылки")
            return
        
        if match.group(2):  # Формат c/chat_id
            chat_identifier = int(match.group(2))
            message_id = int(match.group(4))
        else:  # Формат username
            chat_identifier = match.group(3)
            message_id = int(match.group(4))
        
        await event.reply('Скачиваю...')
        
        file_path, status = await download_media(chat_identifier, message_id)
        
        if file_path:
            await event.reply('Файл скачан!')
            await bot_client.send_file(event.chat_id, file_path)
            # Очистка
            try:
                os.remove(file_path)
            except:
                pass
        else:
            await event.reply(f'Ошибка: {status}')

    # Запускаем бота
    await bot_client.start(bot_token=BOT_TOKEN)
    print("Бот запущен...")
    await bot_client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
