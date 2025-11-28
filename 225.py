import asyncio
from telethon import TelegramClient, events
import re
import os
import json

# Файл для хранения конфигурации
CONFIG_FILE = 'config.json'

async def save_config(api_id, api_hash, session_name='user_session'):
    config = {
        'api_id': api_id,
        'api_hash': api_hash,
        'session_name': session_name
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)
    return True

async def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return None

async def setup_user_session(api_id, api_hash, session_name):
    try:
        client = TelegramClient(session_name, api_id, api_hash)
        await client.start()
        print("User session configured successfully!")
        await client.disconnect()
        return True
    except Exception as e:
        return False, str(e)

async def download_media(chat_identifier, message_id):
    config = await load_config()
    if not config:
        return None, "Конфигурация не настроена"
    
    user_client = None
    try:
        user_client = TelegramClient(config['session_name'], config['api_id'], config['api_hash'])
        await user_client.start()
        
        message = await user_client.get_messages(chat_identifier, ids=message_id)
        
        if not message or not message.media:
            return None, "Сообщение или медиа не найдено"
        
        os.makedirs("downloads", exist_ok=True)
        file_path = await message.download_media(file="downloads/")
        return file_path, "Успешно"
        
    except Exception as e:
        return None, f"Ошибка: {str(e)}"
    finally:
        if user_client:
            await user_client.disconnect()

async def main():
    bot_client = TelegramClient('bot', 1234567, 'temp_hash')  # Временные данные
    
    @bot_client.on(events.NewMessage(pattern='/start'))
    async def start(event):
        config = await load_config()
        if config:
            await event.reply('Бот настроен. Отправь ссылку на сообщение для скачивания.')
        else:
            await event.reply('''Привет! Сначала настрой конфигурацию:
            
/setup API_ID API_HASH
Пример: /setup 1234567 abcdef123456

После настройки отправляй ссылки для скачивания.''')

    @bot_client.on(events.NewMessage(pattern='/setup'))
    async def setup_handler(event):
        try:
            args = event.text.split()
            if len(args) != 3:
                await event.reply('Использование: /setup API_ID API_HASH')
                return
            
            api_id = int(args[1])
            api_hash = args[2]
            
            success = await save_config(api_id, api_hash)
            if success:
                session_result = await setup_user_session(api_id, api_hash, 'user_session')
                if session_result == True:
                    await event.reply('✅ Конфигурация сохранена! Теперь отправляй ссылки для скачивания.')
                else:
                    await event.reply(f'❌ Ошибка настройки сессии: {session_result[1]}')
            else:
                await event.reply('❌ Ошибка сохранения конфигурации')
                
        except ValueError:
            await event.reply('❌ API ID должен быть числом')
        except Exception as e:
            await event.reply(f'❌ Ошибка: {str(e)}')

    @bot_client.on(events.NewMessage)
    async def handle_message(event):
        text = event.text
        
        if text.startswith('/'):
            return
            
        if not text.startswith('https://t.me/'):
            return
            
        config = await load_config()
        if not config:
            await event.reply('❌ Сначала настрой конфигурацию командой /setup')
            return
            
        pattern = r'https://t\.me/(c/(\d+)|(\w+))/(\d+)'
        match = re.search(pattern, text)
        
        if not match:
            await event.reply("❌ Неверный формат ссылки")
            return
        
        chat_identifier = int(match.group(2)) if match.group(2) else match.group(3)
        message_id = int(match.group(4))
        
        await event.reply('⏳ Скачиваю...')
        file_path, status = await download_media(chat_identifier, message_id)
        
        if file_path:
            await bot_client.send_file(event.chat_id, file_path, caption="✅ Скачанный файл")
            os.remove(file_path)
        else:
            await event.reply(f'❌ {status}')

    # Используем временный токен для запуска
    BOT_TOKEN = '7971014285:AAGe6IbdI7_dLHsn3UdGBER-wZRKK-buSys'
    await bot_client.start(bot_token=BOT_TOKEN)
    print("Бот запущен...")
    await bot_client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
