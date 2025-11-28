import os
import logging
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import (
    MessageMediaPhoto, 
    MessageMediaDocument,
    DocumentAttributeVideo,
    DocumentAttributeAudio
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальные переменные для хранения данных авторизации
user_sessions = {}

async def init_bot():
    """Инициализация бота"""
    bot_token = input("7971014285:AAGe6IbdI7_dLHsn3UdGBER-wZRKK-buSys")
    
    # Создаем клиент для бота
    bot = TelegramClient('bot_session', 0, '').start(bot_token=bot_token)
    
    @bot.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        """Обработчик команды /start"""
        await event.reply(
            "👋 Привет! Я бот для скачивания медиафайлов.\n\n"
            "Для начала работы мне нужны твои данные авторизации Telegram.\n"
            "Отправь /auth для начала авторизации"
        )
    
    @bot.on(events.NewMessage(pattern='/auth'))
    async def auth_handler(event):
        """Обработчик команды авторизации"""
        user_id = event.sender_id
        user_sessions[user_id] = {'step': 'api_id'}
        
        await event.reply(
            "🔐 Начинаем процесс авторизации:\n\n"
            "1. Перейди на https://my.telegram.org\n"
            "2. Войди в свой аккаунт\n"
            "3. Перейди в раздел 'API Development Tools'\n"
            "4. Создай приложение и получи API данные\n\n"
            "Теперь введи свой API ID:"
        )
    
    @bot.on(events.NewMessage)
    async def message_handler(event):
        """Обработчик всех сообщений"""
        user_id = event.sender_id
        text = event.text
        
        if user_id not in user_sessions:
            if not text.startswith('/'):
                await event.reply("Для начала работы отправь /start")
            return
        
        session_data = user_sessions[user_id]
        step = session_data.get('step')
        
        if step == 'api_id':
            try:
                api_id = int(text.strip())
                session_data['api_id'] = api_id
                session_data['step'] = 'api_hash'
                await event.reply("✅ API ID принят. Теперь введи API Hash:")
            except ValueError:
                await event.reply("❌ Неверный API ID. Введи число:")
        
        elif step == 'api_hash':
            api_hash = text.strip()
            if len(api_hash) < 10:
                await event.reply("❌ Неверный API Hash. Попробуй еще раз:")
                return
            
            session_data['api_hash'] = api_hash
            session_data['step'] = 'phone'
            await event.reply(
                "✅ API Hash принят. Теперь введи свой номер телефона в международном формате:\n"
                "Пример: +79123456789"
            )
        
        elif step == 'phone':
            phone = text.strip()
            session_data['phone'] = phone
            
            try:
                # Создаем клиент для пользователя
                client = TelegramClient(
                    StringSession(), 
                    session_data['api_id'], 
                    session_data['api_hash']
                )
                
                await client.start(phone=phone)
                
                # Сохраняем сессию
                session_string = client.session.save()
                session_data['session_string'] = session_string
                session_data['client'] = client
                session_data['step'] = 'ready'
                
                await event.reply(
                    "✅ Авторизация успешна! Теперь ты можешь скачивать медиафайлы.\n\n"
                    "Просто пришли мне ссылку на сообщение с фото, видео, голосовым сообщением или видеокружком."
                )
                
            except Exception as e:
                await event.reply(f"❌ Ошибка авторизации: {str(e)}\nПопробуй снова с /auth")
                del user_sessions[user_id]
        
        elif step == 'ready' and text.startswith('http'):
            await download_media(event, session_data['client'])
    
    async def download_media(event, client):
        """Скачивание медиафайла из сообщения"""
        try:
            url = event.text.strip()
            await event.reply("⏳ Скачиваю медиафайл...")
            
            # Получаем информацию о сообщении из ссылки
            message = await client.get_messages(url)
            
            if not message or not message.media:
                await event.reply("❌ Не удалось найти медиафайл в указанном сообщении")
                return
            
            # Скачиваем медиафайл
            filename = await download_file(client, message.media)
            
            if filename:
                # Отправляем файл пользователю
                await event.reply("✅ Файл успешно скачан!")
                await event.respond(file=filename)
                
                # Удаляем временный файл
                os.remove(filename)
            else:
                await event.reply("❌ Не удалось скачать файл")
                
        except Exception as e:
            logger.error(f"Error downloading media: {e}")
            await event.reply(f"❌ Ошибка при скачивании: {str(e)}")
    
    async def download_file(client, media):
        """Скачивание файла и возвращение имени файла"""
        try:
            if isinstance(media, MessageMediaPhoto):
                filename = await client.download_media(media, file="downloads/photo_{}.jpg")
            elif isinstance(media, MessageMediaDocument):
                # Определяем тип документа
                doc = media.document
                attributes = doc.attributes
                
                for attr in attributes:
                    if isinstance(attr, DocumentAttributeVideo):
                        if attr.round_message:  # Видеокружок
                            filename = await client.download_media(media, file="downloads/video_note_{}.mp4")
                        else:  # Обычное видео
                            filename = await client.download_media(media, file="downloads/video_{}.mp4")
                        break
                    elif isinstance(attr, DocumentAttributeAudio):
                        if attr.voice:  # Голосовое сообщение
                            filename = await client.download_media(media, file="downloads/voice_{}.ogg")
                        else:  # Аудиофайл
                            filename = await client.download_media(media, file="downloads/audio_{}.mp3")
                        break
                else:
                    # Другие типы документов
                    filename = await client.download_media(media, file="downloads/document_{}")
            else:
                return None
                
            return filename
        except Exception as e:
            logger.error(f"Error in download_file: {e}")
            return None
    
    # Создаем папку для загрузок
    os.makedirs('downloads', exist_ok=True)
    
    return bot

if __name__ == "__main__":
    print("🤖 Инициализация Telegram бота...")
    
    # Запускаем бота
    loop = asyncio.get_event_loop()
    bot = loop.run_until_complete(init_bot())
    
    print("✅ Бот запущен!")
    print("Отправь /start в Telegram для начала работы")
    
    # Запускаем бесконечный цикл
    bot.run_until_disconnected()
