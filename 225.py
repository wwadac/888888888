import asyncio
import logging
import time
import sqlite3
import os
import re
from telethon import TelegramClient, events, Button
from telethon.tl.types import Document, MessageMediaDocument

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileTransferBot:
    def __init__(self):
        self.API_ID = '29385016'
        self.API_HASH = '3c57df8805ab5de5a23a032ed39b9af9'
        self.BOT_TOKEN = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'
        
        self.bot_client = None
        self.user_client = None
        self.setup_database()
        self.allowed_extensions = ['.zip', '.rar', '.py']
        self.transfer_tasks = {}
    
    def setup_database(self):
        """Настройка базы данных для хранения каналов и настроек"""
        self.conn = sqlite3.connect('file_transfer.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Таблица для каналов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_channel TEXT UNIQUE,
                destination_channel TEXT,
                added_time REAL
            )
        ''')
        
        # Таблица для настроек
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY,
                interval INTEGER DEFAULT 10,
                max_files INTEGER DEFAULT 100
            )
        ''')
        
        # Добавляем настройки по умолчанию
        self.cursor.execute('INSERT OR IGNORE INTO settings (id, interval, max_files) VALUES (1, 10, 100)')
        self.conn.commit()
    
    async def initialize(self):
        """Инициализация бота и пользовательского клиента"""
        # Бот клиент для команд
        self.bot_client = TelegramClient(
            'bot_session', 
            self.API_ID, 
            self.API_HASH
        )
        
        # Пользовательский клиент для пересылки файлов
        self.user_client = TelegramClient(
            'user_session',
            self.API_ID,
            self.API_HASH
        )
        
        await self.bot_client.start(bot_token=self.BOT_TOKEN)
        await self.user_client.start()
        
        self.setup_handlers()
        logger.info("Бот инициализирован")
    
    def setup_handlers(self):
        """Настройка обработчиков событий"""
        
        @self.bot_client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            """Главное меню"""
            menu_text = """
📁 **File Transfer Bot**

Пересылает файлы (zip/rar/py) между каналами

**Команды:**
/add_channel - Добавить канал
/remove_channel - Удалить канал  
/list_channels - Список каналов
/settings - Настройки
/transfer - Начать пересылку
/stop - Остановить пересылку
/stats - Статистика
            """
            buttons = [
                [Button.inline("📥 Добавить канал", b"add_channel"),
                 Button.inline("📤 Список каналов", b"list_channels")],
                [Button.inline("⚙️ Настройки", b"settings"),
                 Button.inline("🔄 Начать пересылку", b"start_transfer")]
            ]
            await event.reply(menu_text, buttons=buttons)
        
        @self.bot_client.on(events.NewMessage(pattern='/add_channel'))
        async def add_channel_handler(event):
            """Добавление канала"""
            await event.reply("""
📥 **Добавление канала**

Отправьте в формате:
`источник -> назначение`

**Пример:**
@source_channel -> @destination_channel
-100123456789 -> -100987654321

Или просто @username для тестового режима
            """)
        
        @self.bot_client.on(events.NewMessage(pattern='/list_channels'))
        async def list_channels_handler(event):
            """Список каналов"""
            channels = self.get_channels()
            if not channels:
                await event.reply("❌ Каналы не добавлены")
                return
            
            text = "📋 **Список каналов:**\n\n"
            for i, channel in enumerate(channels, 1):
                text += f"{i}. {channel[1]} → {channel[2]}\n"
            
            await event.reply(text)
        
        @self.bot_client.on(events.NewMessage(pattern='/settings'))
        async def settings_handler(event):
            """Настройки бота"""
            settings = self.get_settings()
            text = f"""
⚙️ **Настройки бота**

📊 Интервал: {settings['interval']} секунд
📁 Макс. файлов за раз: {settings['max_files']}

Используйте:
/set_interval [секунды] - изменить интервал
/set_max [число] - изменить максимум файлов
            """
            await event.reply(text)
        
        @self.bot_client.on(events.NewMessage(pattern='/set_interval'))
        async def set_interval_handler(event):
            """Установка интервала"""
            try:
                parts = event.text.split()
                if len(parts) < 2:
                    await event.reply("❌ Использование: /set_interval [секунды]")
                    return
                
                interval = int(parts[1])
                if interval < 1:
                    await event.reply("❌ Интервал должен быть не менее 1 секунды")
                    return
                
                self.update_setting('interval', interval)
                await event.reply(f"✅ Интервал установлен: {interval} секунд")
                
            except ValueError:
                await event.reply("❌ Введите число")
        
        @self.bot_client.on(events.NewMessage(pattern='/set_max'))
        async def set_max_handler(event):
            """Установка максимального количества файлов"""
            try:
                parts = event.text.split()
                if len(parts) < 2:
                    await event.reply("❌ Использование: /set_max [число]")
                    return
                
                max_files = int(parts[1])
                if max_files < 1:
                    await event.reply("❌ Количество должно быть не менее 1")
                    return
                
                self.update_setting('max_files', max_files)
                await event.reply(f"✅ Максимум файлов установлен: {max_files}")
                
            except ValueError:
                await event.reply("❌ Введите число")
        
        @self.bot_client.on(events.NewMessage(pattern='/transfer'))
        async def transfer_handler(event):
            """Начало пересылки"""
            user_id = event.sender_id
            channels = self.get_channels()
            
            if not channels:
                await event.reply("❌ Сначала добавьте каналы")
                return
            
            if user_id in self.transfer_tasks:
                await event.reply("❌ Пересылка уже запущена")
                return
            
            # Запускаем пересылку
            task = asyncio.create_task(self.start_file_transfer(event, user_id))
            self.transfer_tasks[user_id] = task
            
            await event.reply("🔄 Запускаю пересылку файлов...")
        
        @self.bot_client.on(events.NewMessage(pattern='/stop'))
        async def stop_handler(event):
            """Остановка пересылки"""
            user_id = event.sender_id
            
            if user_id in self.transfer_tasks:
                self.transfer_tasks[user_id].cancel()
                del self.transfer_tasks[user_id]
                await event.reply("⏹️ Пересылка остановлена")
            else:
                await event.reply("❌ Пересылка не запущена")
        
        @self.bot_client.on(events.CallbackQuery)
        async def callback_handler(event):
            """Обработчик inline кнопок"""
            data = event.data.decode('utf-8')
            user_id = event.sender_id
            
            if data == "add_channel":
                await add_channel_handler(event)
            elif data == "list_channels":
                await list_channels_handler(event)
            elif data == "settings":
                await settings_handler(event)
            elif data == "start_transfer":
                await transfer_handler(event)
        
        @self.bot_client.on(events.NewMessage)
        async def message_handler(event):
            """Обработчик обычных сообщений"""
            text = event.text.strip()
            
            if text.startswith('/'):
                return
            
            # Обработка добавления канала
            if '->' in text:
                await self.process_add_channel(event, text)
    
    async def process_add_channel(self, event, text):
        """Обработка добавления канала"""
        try:
            parts = text.split('->')
            if len(parts) != 2:
                await event.reply("❌ Неверный формат. Используйте: источник -> назначение")
                return
            
            source = parts[0].strip()
            destination = parts[1].strip()
            
            # Сохраняем в базу
            self.cursor.execute(
                'INSERT OR REPLACE INTO channels (source_channel, destination_channel, added_time) VALUES (?, ?, ?)',
                (source, destination, time.time())
            )
            self.conn.commit()
            
            await event.reply(f"✅ Канал добавлен:\n{source} → {destination}")
            
        except Exception as e:
            await event.reply(f"❌ Ошибка: {e}")
    
    def get_channels(self):
        """Получить список каналов"""
        self.cursor.execute('SELECT * FROM channels')
        return self.cursor.fetchall()
    
    def get_settings(self):
        """Получить настройки"""
        self.cursor.execute('SELECT * FROM settings WHERE id = 1')
        result = self.cursor.fetchone()
        return {'interval': result[1], 'max_files': result[2]}
    
    def update_setting(self, setting, value):
        """Обновить настройку"""
        self.cursor.execute(f'UPDATE settings SET {setting} = ? WHERE id = 1', (value,))
        self.conn.commit()
    
    def is_allowed_file(self, document):
        """Проверить, разрешен ли файл"""
        if not document or not hasattr(document, 'attributes'):
            return False
        
        for attr in document.attributes:
            if hasattr(attr, 'file_name'):
                file_name = attr.file_name.lower()
                return any(file_name.endswith(ext) for ext in self.allowed_extensions)
        return False
    
    async def start_file_transfer(self, event, user_id):
        """Запуск пересылки файлов"""
        try:
            channels = self.get_channels()
            settings = self.get_settings()
            
            transferred_count = 0
            
            for channel in channels:
                source = channel[1]
                destination = channel[2]
                
                await event.reply(f"🔄 Начинаю пересылку из {source} в {destination}")
                
                try:
                    # Получаем сообщения из исходного канала
                    async for message in self.user_client.iter_messages(source):
                        if transferred_count >= settings['max_files']:
                            await event.reply(f"✅ Достигнут лимит в {settings['max_files']} файлов")
                            return
                        
                        # Проверяем, что это файл и он разрешен
                        if message.media and isinstance(message.media, MessageMediaDocument):
                            document = message.media.document
                            if self.is_allowed_file(document):
                                
                                # Пересылаем файл
                                await self.user_client.send_message(destination, message)
                                transferred_count += 1
                                
                                await event.reply(f"📁 Переслано файлов: {transferred_count}")
                                
                                # Ждем интервал
                                await asyncio.sleep(settings['interval'])
                
                except Exception as e:
                    await event.reply(f"❌ Ошибка в канале {source}: {e}")
                    continue
            
            await event.reply(f"✅ Пересылка завершена! Всего файлов: {transferred_count}")
            
        except asyncio.CancelledError:
            await event.reply("⏹️ Пересылка прервана пользователем")
        except Exception as e:
            await event.reply(f"❌ Ошибка пересылки: {e}")
        finally:
            if user_id in self.transfer_tasks:
                del self.transfer_tasks[user_id]
    
    async def run(self):
        """Запуск бота"""
        await self.initialize()
        logger.info("File Transfer Bot запущен и готов к работе")
        
        me = await self.bot_client.get_me()
        logger.info(f"Бот @{me.username} успешно запущен!")
        
        await self.bot_client.run_until_disconnected()

# Запуск бота
if __name__ == '__main__':
    bot = FileTransferBot()
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        if hasattr(bot, 'conn'):
            bot.conn.close()
