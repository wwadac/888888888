import asyncio
import logging
import time
import sqlite3
import os
from telethon import TelegramClient, events, Button
from telethon.tl.types import Document, MessageMediaDocument

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChannelStatsBot:
    def __init__(self):
        self.API_ID = '29385016'
        self.API_HASH = '3c57df8805ab5de5a23a032ed39b9af9'
        self.BOT_TOKEN = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'
        
        self.bot_client = None
        self.user_client = None
        self.setup_database()
    
    def setup_database(self):
        """Настройка базы данных для каналов"""
        self.conn = sqlite3.connect('channels.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                title TEXT,
                participants_count INTEGER,
                files_count INTEGER,
                voices_count INTEGER,
                last_checked REAL
            )
        ''')
        self.conn.commit()
    
    async def initialize(self):
        """Инициализация бота"""
        self.bot_client = TelegramClient(
            'bot_session', 
            self.API_ID, 
            self.API_HASH
        )
        
        await self.bot_client.start(bot_token=self.BOT_TOKEN)
        
        # Проверяем есть ли файл сессии пользователя
        if os.path.exists('user_session.session'):
            self.user_client = TelegramClient('user_session', self.API_ID, self.API_HASH)
            await self.user_client.start()
            logger.info("✅ User client запущен!")
        else:
            logger.warning("❌ Файл сессии не найден. Используй команду /create_session")
            self.user_client = None
        
        self.setup_handlers()
        logger.info("Бот инициализирован")
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        
        @self.bot_client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            status = "✅ Аккаунт подключен" if self.user_client else "❌ Требуется сессия"
            menu_text = f"""
📊 Channel Stats Bot

Статус: {status}
Анализ от: Твой аккаунт

Команды:
/stats @channel - Статистика канала
/create_session - Создать сессию
/list - Список каналов
/help - Помощь
            """
            await event.reply(menu_text)
        
        @self.bot_client.on(events.NewMessage(pattern='/create_session'))
        async def create_session_handler(event):
            """Инструкция по созданию сессии"""
            instruction = """
📝 Как создать сессию:

1. На локальном компьютере создай файл:
```python
# create_session.py
import asyncio
from telethon import TelegramClient

async def main():
    client = TelegramClient('user_session', 29385016, '3c57df8805ab5de5a23a032ed39b9af9')
    await client.start()
    print("Сессия создана!")
    await client.disconnect()

asyncio.run(main())
