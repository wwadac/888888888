import asyncio
import logging
import time
import sqlite3
from telethon import TelegramClient, events, Button

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileTransferBot:
    def __init__(self):
        self.API_ID = '29385016'
        self.API_HASH = '3c57df8805ab5de5a23a032ed39b9af9'
        self.BOT_TOKEN = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'
        
        self.bot_client = None
        self.setup_database()
        self.allowed_extensions = ['.zip', '.rar', '.py']
        self.transfer_tasks = {}
    
    def setup_database(self):
        """Настройка базы данных"""
        self.conn = sqlite3.connect('file_transfer.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_channel TEXT UNIQUE,
                destination_channel TEXT,
                added_time REAL
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY,
                interval INTEGER DEFAULT 10,
                max_files INTEGER DEFAULT 100
            )
        ''')
        
        self.cursor.execute('INSERT OR IGNORE INTO settings (id, interval, max_files) VALUES (1, 10, 100)')
        self.conn.commit()
    
    async def initialize(self):
        """Инициализация только бота"""
        self.bot_client = TelegramClient(
            'bot_session', 
            self.API_ID, 
            self.API_HASH
        )
        
        await self.bot_client.start(bot_token=self.BOT_TOKEN)
        self.setup_handlers()
        logger.info("Бот инициализирован")
    
    def setup_handlers(self):
        """Настройка обработчиков"""
        
        @self.bot_client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            menu_text = """
📁 File Transfer Bot

Пересылает файлы (zip/rar/py) между каналами

Команды:
/add_channel - Добавить канал
/list_channels - Список каналов  
/settings - Настройки
/help - Помощь
            """
            await event.reply(menu_text)
        
        @self.bot_client.on(events.NewMessage(pattern='/help'))
        async def help_handler(event):
            help_text = """
📖 Помощь по боту

Для работы бота нужно:
1. Добавить каналы командой /add_channel
2. Настроить интервал /settings
3. Бот будет работать от своего имени

Форматы каналов:
@username
-100123456789
https://t.me/channelname

Пример добавления:
/add_channel @source @destination
            """
            await event.reply(help_text)
        
        @self.bot_client.on(events.NewMessage(pattern='/add_channel'))
        async def add_channel_handler(event):
            try:
                parts = event.text.split()
                if len(parts) < 3:
                    await event.reply("Использование: /add_channel @source @destination")
                    return
                
                source = parts[1]
                destination = parts[2]
                
                self.cursor.execute(
                    'INSERT OR REPLACE INTO channels (source_channel, destination_channel, added_time) VALUES (?, ?, ?)',
                    (source, destination, time.time())
                )
                self.conn.commit()
                
                await event.reply(f"✅ Канал добавлен:\n{source} → {destination}")
                
            except Exception as e:
                await event.reply(f"❌ Ошибка: {e}")
        
        @self.bot_client.on(events.NewMessage(pattern='/list_channels'))
        async def list_channels_handler(event):
            channels = self.get_channels()
            if not channels:
                await event.reply("❌ Каналы не добавлены")
                return
            
            text = "📋 Список каналов:\n\n"
            for i, channel in enumerate(channels, 1):
                text += f"{i}. {channel[1]} → {channel[2]}\n"
            
            await event.reply(text)
        
        @self.bot_client.on(events.NewMessage(pattern='/settings'))
        async def settings_handler(event):
            settings = self.get_settings()
            text = f"""
⚙️ Настройки бота

Интервал: {settings['interval']} секунд
Макс. файлов: {settings['max_files']}

Команды:
/set_interval [секунды]
/set_max [число]
            """
            await event.reply(text)
        
        @self.bot_client.on(events.NewMessage(pattern='/set_interval'))
        async def set_interval_handler(event):
            try:
                parts = event.text.split()
                if len(parts) < 2:
                    await event.reply("Использование: /set_interval [секунды]")
                    return
                
                interval = int(parts[1])
                if interval < 1:
                    await event.reply("Интервал должен быть не менее 1 секунды")
                    return
                
                self.update_setting('interval', interval)
                await event.reply(f"✅ Интервал установлен: {interval} секунд")
                
            except ValueError:
                await event.reply("Введите число")
        
        @self.bot_client.on(events.NewMessage(pattern='/set_max'))
        async def set_max_handler(event):
            try:
                parts = event.text.split()
                if len(parts) < 2:
                    await event.reply("Использование: /set_max [число]")
                    return
                
                max_files = int(parts[1])
                if max_files < 1:
                    await event.reply("Количество должно быть не менее 1")
                    return
                
                self.update_setting('max_files', max_files)
                await event.reply(f"✅ Максимум файлов установлен: {max_files}")
                
            except ValueError:
                await event.reply("Введите число")
        
        @self.bot_client.on(events.NewMessage(pattern='/test'))
        async def test_handler(event):
            """Тестовая команда для проверки работы"""
            await event.reply("🤖 Бот работает корректно!")
    
    def get_channels(self):
        self.cursor.execute('SELECT * FROM channels')
        return self.cursor.fetchall()
    
    def get_settings(self):
        self.cursor.execute('SELECT * FROM settings WHERE id = 1')
        result = self.cursor.fetchone()
        return {'interval': result[1], 'max_files': result[2]}
    
    def update_setting(self, setting, value):
        self.cursor.execute(f'UPDATE settings SET {setting} = ? WHERE id = 1', (value,))
        self.conn.commit()
    
    async def run(self):
        await self.initialize()
        logger.info("File Transfer Bot запущен")
        
        me = await self.bot_client.get_me()
        logger.info(f"Бот @{me.username} работает")
        
        await self.bot_client.run_until_disconnected()

# Запуск бота
if __name__ == '__main__':
    bot = FileTransferBot()
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        if hasattr(bot, 'conn'):
            bot.conn.close()
