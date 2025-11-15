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
        self.waiting_for_channel = {}  # Для пошагового добавления каналов
    
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
/transfer - Начать пересылку
/help - Помощь
            """
            buttons = [
                [Button.inline("➕ Добавить канал", b"add_channel_menu")],
                [Button.inline("📋 Список каналов", b"list_channels")],
                [Button.inline("⚙️ Настройки", b"show_settings")]
            ]
            await event.reply(menu_text, buttons=buttons)
        
        @self.bot_client.on(events.NewMessage(pattern='/add_channel'))
        async def add_channel_handler(event):
            """Начинаем процесс добавления канала"""
            user_id = event.sender_id
            self.waiting_for_channel[user_id] = 'waiting_source'
            
            await event.reply("""
📥 Добавление канала

Шаг 1/2: Отправьте исходный канал (откуда брать файлы)

Можно в формате:
@username
-1002550241842
https://t.me/channelname
            """)
        
        @self.bot_client.on(events.NewMessage(pattern='/list_channels'))
        async def list_channels_handler(event):
            """Список каналов"""
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
            """Настройки бота"""
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
            """Установка интервала"""
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
            """Установка максимального количества файлов"""
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
        
        @self.bot_client.on(events.NewMessage(pattern='/transfer'))
        async def transfer_handler(event):
            """Начать пересылку"""
            channels = self.get_channels()
            if not channels:
                await event.reply("❌ Сначала добавьте каналы через /add_channel")
                return
            
            await event.reply("🔄 Пересылка файлов... (функция в разработке)")
            # Здесь будет код пересылки файлов
        
        @self.bot_client.on(events.CallbackQuery)
        async def callback_handler(event):
            """Обработчик inline кнопок"""
            data = event.data.decode('utf-8')
            user_id = event.sender_id
            
            if data == "add_channel_menu":
                await add_channel_handler(event)
            elif data == "list_channels":
                await list_channels_handler(event)
            elif data == "show_settings":
                await settings_handler(event)
        
        @self.bot_client.on(events.NewMessage)
        async def message_handler(event):
            """Обработчик обычных сообщений для пошагового добавления каналов"""
            user_id = event.sender_id
            text = event.text.strip()
            
            if text.startswith('/'):
                return
            
            # Проверяем, находится ли пользователь в процессе добавления канала
            if user_id in self.waiting_for_channel:
                step = self.waiting_for_channel[user_id]
                
                if step == 'waiting_source':
                    # Сохраняем исходный канал и запрашиваем целевой
                    source_channel = self.clean_channel_input(text)
                    self.waiting_for_channel[user_id] = {
                        'step': 'waiting_destination',
                        'source': source_channel
                    }
                    
                    await event.reply(f"""
✅ Исходный канал: {source_channel}

Шаг 2/2: Отправьте целевой канал (куда пересылать файлы)

Формат:
@username  
-1002550241842
https://t.me/channelname
                    """)
                
                elif step['step'] == 'waiting_destination':
                    # Сохраняем целевой канал в базу
                    destination_channel = self.clean_channel_input(text)
                    source_channel = step['source']
                    
                    try:
                        self.cursor.execute(
                            'INSERT OR REPLACE INTO channels (source_channel, destination_channel, added_time) VALUES (?, ?, ?)',
                            (source_channel, destination_channel, time.time())
                        )
                        self.conn.commit()
                        
                        await event.reply(f"""
✅ Канал успешно добавлен!

📥 Источник: {source_channel}
📤 Назначение: {destination_channel}

Теперь можно начать пересылку файлов командой /transfer
                        """)
                        
                    except Exception as e:
                        await event.reply(f"❌ Ошибка при добавлении канала: {e}")
                    
                    # Очищаем состояние пользователя
                    if user_id in self.waiting_for_channel:
                        del self.waiting_for_channel[user_id]
    
    def clean_channel_input(self, text):
        """Очищает ввод канала от лишних символов"""
        # Убираем пробелы
        text = text.strip()
        
        # Если это URL, извлекаем username
        if 't.me/' in text:
            if text.startswith('https://t.me/'):
                text = '@' + text.split('https://t.me/')[-1]
            elif text.startswith('t.me/'):
                text = '@' + text.split('t.me/')[-1]
        
        # Убираем @ если их несколько
        if text.startswith('@@'):
            text = '@' + text[2:]
        
        return text
    
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
