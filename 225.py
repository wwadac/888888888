import asyncio
import logging
import time
import sqlite3
from telethon import TelegramClient, events, Button

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChannelStatsBot:
    def __init__(self):
        self.API_ID = '29385016'
        self.API_HASH = '3c57df8805ab5de5a23a032ed39b9af9'
        self.BOT_TOKEN = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'
        
        self.bot_client = None
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
            'session_bot', 
            self.API_ID, 
            self.API_HASH
        )
        
        await self.bot_client.start(bot_token=self.BOT_TOKEN)
        self.setup_handlers()
        logger.info("Бот инициализирован")
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        
        @self.bot_client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            menu_text = """
📊 Channel Stats Bot

Анализирует статистику каналов и групп

Команды:
/stats @channel - Статистика канала
/add @channel - Добавить в базу
/list - Список каналов
/scan_all - Просканировать все
/help - Помощь
            """
            await event.reply(menu_text)
        
        @self.bot_client.on(events.NewMessage(pattern='/stats'))
        async def stats_handler(event):
            """Анализ статистики канала"""
            try:
                parts = event.text.split()
                if len(parts) < 2:
                    await event.reply("Использование: /stats @channel")
                    return
                
                channel_input = parts[1].replace('@', '')
                await event.reply(f"🔍 Анализирую @{channel_input}...")
                
                # Анализируем канал
                result = await self.analyze_channel(channel_input)
                
                if result:
                    response = f"""
📊 Статистика: @{channel_input}

📢 Название: {result['title']}
👥 Участники: {result['participants_count']}
📁 Файлы: {result['files_count']}
🎤 Голосовые: {result['voices_count']}
📅 Сообщений: {result['total_messages']}
                    """
                else:
                    response = f"❌ Не удалось проанализировать @{channel_input}"
                
                await event.reply(response)
                
            except Exception as e:
                await event.reply(f"❌ Ошибка: {e}")
        
        @self.bot_client.on(events.NewMessage(pattern='/add'))
        async def add_handler(event):
            """Добавить канал в базу"""
            try:
                parts = event.text.split()
                if len(parts) < 2:
                    await event.reply("Использование: /add @channel")
                    return
                
                channel_input = parts[1].replace('@', '')
                
                # Сохраняем в базу
                self.cursor.execute(
                    'INSERT OR IGNORE INTO channels (username, last_checked) VALUES (?, ?)',
                    (channel_input, time.time())
                )
                self.conn.commit()
                
                await event.reply(f"✅ Канал @{channel_input} добавлен")
                
            except Exception as e:
                await event.reply(f"❌ Ошибка: {e}")
        
        @self.bot_client.on(events.NewMessage(pattern='/list'))
        async def list_handler(event):
            """Список каналов в базе"""
            channels = self.get_channels()
            if not channels:
                await event.reply("❌ В базе нет каналов")
                return
            
            text = "📋 Каналы в базе:\n\n"
            for i, channel in enumerate(channels, 1):
                status = "✅" if channel[4] else "❌"
                text += f"{i}. {status} @{channel[1]}\n"
            
            await event.reply(text)
        
        @self.bot_client.on(events.NewMessage(pattern='/scan_all'))
        async def scan_all_handler(event):
            """Сканировать все каналы из базы"""
            channels = self.get_channels()
            if not channels:
                await event.reply("❌ В базе нет каналов")
                return
            
            await event.reply(f"🔄 Сканирую {len(channels)} каналов...")
            
            scanned = 0
            for channel in channels:
                try:
                    username = channel[1]
                    result = await self.analyze_channel(username)
                    if result:
                        # Обновляем данные в базе
                        self.update_channel_stats(
                            username,
                            result['title'],
                            result['participants_count'],
                            result['files_count'],
                            result['voices_count']
                        )
                        scanned += 1
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    continue
            
            await event.reply(f"✅ Сканирование завершено! Обработано: {scanned} каналов")
    
    async def analyze_channel(self, username):
        """Анализ канала - подсчет файлов, голосовых"""
        try:
            # Получаем информацию о канале
            channel = await self.bot_client.get_entity(username)
            
            files_count = 0
            voices_count = 0
            total_messages = 0
            
            # Анализируем сообщения
            async for message in self.bot_client.iter_messages(channel, limit=500):
                total_messages += 1
                
                if message.document:
                    files_count += 1
                    # Проверяем голосовые сообщения
                    if hasattr(message.document, 'mime_type') and message.document.mime_type == 'audio/ogg':
                        voices_count += 1
                elif message.voice:
                    voices_count += 1
            
            # Получаем количество участников
            participants_count = 0
            try:
                participants_count = getattr(channel, 'participants_count', 0)
            except:
                pass
            
            return {
                'title': getattr(channel, 'title', 'Неизвестно'),
                'participants_count': participants_count,
                'files_count': files_count,
                'voices_count': voices_count,
                'total_messages': total_messages
            }
            
        except Exception as e:
            logger.error(f"Ошибка анализа канала @{username}: {e}")
            return None
    
    def get_channels(self):
        """Получить список каналов"""
        self.cursor.execute('SELECT * FROM channels')
        return self.cursor.fetchall()
    
    def update_channel_stats(self, username, title, participants, files, voices):
        """Обновить статистику канала"""
        self.cursor.execute('''
            UPDATE channels 
            SET title = ?, participants_count = ?, files_count = ?, voices_count = ?, last_checked = ?
            WHERE username = ?
        ''', (title, participants, files, voices, time.time(), username))
        self.conn.commit()
    
    async def run(self):
        await self.initialize()
        logger.info("Channel Stats Bot запущен")
        await self.bot_client.run_until_disconnected()

# Запуск бота
if __name__ == '__main__':
    bot = ChannelStatsBot()
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        if hasattr(bot, 'conn'):
            bot.conn.close()
