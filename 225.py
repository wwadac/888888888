import asyncio
import logging
import sqlite3
import os
from telethon import TelegramClient, events

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserParserBot:
    def __init__(self):
        self.API_ID = '29385016'
        self.API_HASH = '3c57df8805ab5de5a23a032ed39b9af9'
        self.BOT_TOKEN = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'
        
        self.bot_client = None
        self.user_client = None
        self.setup_database()
    
    def setup_database(self):
        """Настройка базы данных"""
        self.conn = sqlite3.connect('users.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                chat_source TEXT,
                added_time REAL
            )
        ''')
        self.conn.commit()
    
    async def initialize(self):
        """Инициализация бота"""
        self.bot_client = TelegramClient('bot_session', self.API_ID, self.API_HASH)
        await self.bot_client.start(bot_token=self.BOT_TOKEN)
        
        if os.path.exists('user_session.session'):
            self.user_client = TelegramClient('user_session', self.API_ID, self.API_HASH)
            await self.user_client.start()
            logger.info("✅ Аккаунт подключен")
        else:
            logger.warning("❌ Файл сессии не найден")
            self.user_client = None
        
        self.setup_handlers()
        logger.info("Бот запущен")
    
    def setup_handlers(self):
        """Обработчики команд"""
        
        @self.bot_client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            menu_text = """
👤 User Parser Bot

Парсит юзернеймы из публичных чатов

Команды:
/parse @chat - Спарсить пользователей
/download - Скачать базу в txt
/stats - Статистика
            """
            await event.reply(menu_text)
        
        @self.bot_client.on(events.NewMessage(pattern='/parse'))
        async def parse_handler(event):
            if not self.user_client:
                await event.reply("❌ Аккаунт не подключен")
                return
            
            try:
                parts = event.text.split()
                if len(parts) < 2:
                    await event.reply("Использование: /parse @chat")
                    return
                
                chat_input = parts[1]
                await event.reply(f"🔍 Начинаю парсинг {chat_input}...")
                
                # Парсим пользователей
                result = await self.parse_chat_users(chat_input, event)
                
                await event.reply(f"✅ Готово! Спарсено: {result} пользователей")
                
            except Exception as e:
                await event.reply(f"❌ Ошибка: {e}")
        
        @self.bot_client.on(events.NewMessage(pattern='/download'))
        async def download_handler(event):
            """Скачать базу в txt"""
            try:
                users = self.get_all_users()
                if not users:
                    await event.reply("❌ В базе нет пользователей")
                    return
                
                # Создаем txt файл
                filename = f"users_{int(time.time())}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("Спарсенные пользователи:\n\n")
                    for user in users:
                        username = user[1] or 'нет'
                        first_name = user[2] or ''
                        last_name = user[3] or ''
                        f.write(f"@{username} | {first_name} {last_name}\n")
                
                # Отправляем файл
                await event.reply("📁 Файл готов:")
                await event.reply(file=filename)
                
                # Удаляем временный файл
                os.remove(filename)
                
            except Exception as e:
                await event.reply(f"❌ Ошибка: {e}")
        
        @self.bot_client.on(events.NewMessage(pattern='/stats'))
        async def stats_handler(event):
            """Статистика базы"""
            stats = self.get_stats()
            text = f"""
📊 Статистика:

Всего пользователей: {stats['total']}
Уникальных чатов: {stats['chats']}
            """
            await event.reply(text)
    
    async def parse_chat_users(self, chat_input, event):
        """Парсинг пользователей из чата"""
        try:
            chat = await self.user_client.get_entity(chat_input)
            count = 0
            
            async for user in self.user_client.iter_participants(chat):
                # Сохраняем в базу
                self.cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (id, username, first_name, last_name, phone, chat_source, added_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user.id,
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.phone,
                    chat_input,
                    time.time()
                ))
                
                count += 1
                
                # Отправляем прогресс каждые 50 пользователей
                if count % 50 == 0:
                    await event.reply(f"📊 Спарсено: {count} пользователей")
            
            self.conn.commit()
            return count
            
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")
            return 0
    
    def get_all_users(self):
        """Получить всех пользователей"""
        self.cursor.execute('SELECT * FROM users')
        return self.cursor.fetchall()
    
    def get_stats(self):
        """Статистика базы"""
        self.cursor.execute('SELECT COUNT(*) FROM users')
        total = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT COUNT(DISTINCT chat_source) FROM users')
        chats = self.cursor.fetchone()[0]
        
        return {'total': total, 'chats': chats}
    
    async def run(self):
        await self.initialize()
        await self.bot_client.run_until_disconnected()

if __name__ == '__main__':
    bot = UserParserBot()
    asyncio.run(bot.run())
