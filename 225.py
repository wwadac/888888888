import asyncio
from telethon import TelegramClient, events
import re
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# НАСТРОЙКИ
API_ID = 29385016
API_HASH = '3c57df8805ab5de5a23a032ed39b9af9'
BOT_TOKEN = '7971014285:AAGe6IbdI7_dLHsn3UdGBER-wZRKK-buSys'
USER_SESSION = 'user_account.session'

async def download_media(chat_identifier, message_id):
    user_client = None
    try:
        user_client = TelegramClient(USER_SESSION, API_ID, API_HASH)
        await user_client.start()
        
        message = await user_client.get_messages(chat_identifier, ids=message_id)
        
        if not message or not message.media:
            return None, "Сообщение или медиа не найдено"
        
        os.makedirs("downloads", exist_ok=True)
        file_path = await message.download_media(file="downloads/")
        return file_path, "Успешно"
        
    except Exception as e:
        logger.error(f"Ошибка скачивания: {e}")
        return None, f"Ошибка: {str(e)}"
    finally:
        if user_client:
            await user_client.disconnect()

async def main():
    bot_client = TelegramClient('bot', API_ID, API_HASH)
    
    @bot_client.on(events.NewMessage(pattern='/start'))
    async def start(event):
        await event.reply('''🤖 Бот для скачивания медиа из Telegram

Отправь ссылку на сообщение в формате:
https://t.me/username/123
https://t.me/c/chat_id/123''')

    @bot_client.on(events.NewMessage(pattern='/help'))
    async def help_command(event):
        await event.reply('''📖 Помощь:
Просто отправьте ссылку на сообщение с медиафайлом
Поддерживаемые форматы ссылок:
• https://t.me/username/123
• https://t.me/c/chat_id/123''')

    @bot_client.on(events.NewMessage)
    async def handle_message(event):
        # Игнорируем команды
        if event.text.startswith('/'):
            return
            
        text = event.text
        
        if not text.startswith('https://t.me/'):
            await event.reply("❌ Отправьте ссылку на сообщение в формате: https://t.me/username/123")
            return
            
        pattern = r'https://t\.me/(c/(\d+)|(\w+))/(\d+)'
        match = re.search(pattern, text)
        
        if not match:
            await event.reply("❌ Неверный формат ссылки")
            return
        
        if match.group(2):  # Формат c/chat_id
            chat_identifier = int(match.group(2))
            message_id = int(match.group(4))
        else:  # Формат username
            chat_identifier = match.group(3)
            message_id = int(match.group(4))
        
        processing_msg = await event.reply('⏳ Скачиваю...')
        
        file_path, status = await download_media(chat_identifier, message_id)
        
        if file_path:
            await processing_msg.edit('✅ Файл скачан! Отправляю...')
            await bot_client.send_file(event.chat_id, file_path, caption="📁 Ваш файл")
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Ошибка удаления файла: {e}")
            await processing_msg.delete()
        else:
            await processing_msg.edit(f'❌ Ошибка: {status}')

    try:
        await bot_client.start(bot_token=BOT_TOKEN)
        logger.info("Бот успешно запущен!")
        await bot_client.run_until_disconnected()
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")

if __name__ == '__main__':
    asyncio.run(main())
