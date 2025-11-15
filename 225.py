import asyncio
import logging
import time
import sqlite3
import os
from telethon import TelegramClient, events, Button
from telethon.tl.types import Document, MessageMediaDocument

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChannelAnalyzerBot:
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
        """Инициализация бота и пользовательского клиента"""
        # Бот для команд
        self.bot_client = TelegramClient('bot_session', self.API_ID, self.API_HASH)
        await self.bot_client.start(bot_token=self.BOT_TOKEN)
        
        # Пользовательский клиент для анализа (ТВОЙ аккаунт)
        if os.path.exists('user_session.session'):
            self.user_client = TelegramClient('user_session', self.API_ID, self.API_HASH)
            await self.user_client.start()
            logger.info("✅ User client запущен от твоего аккаунта!")
            
            # Проверяем какой аккаунт
            me = await self.user_client.get_me()
            logger.info(f"🔑 Работаем от: {me.first_name} (@{me.username})")
        else:
            logger.warning("❌ Файл сессии не найден. Анализ не будет работать!")
            self.user_client = None
        
        self.setup_handlers()
        logger.info("Бот инициализирован")
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        
        @self.bot_client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            status = "✅ Готов к работе" if self.user_client else "❌ Требуется сессия"
            menu_text = f"""
📊 Channel Analyzer Bot

Статус: {status}
Аккаунт: Твой личный аккаунт

Команды:
/analyze @channel - Проанализировать канал
/add_channel @channel - Добавить канал в базу
/list_channels - Список каналов в базе
/stats - Статистика всех каналов
/scan_all - Просканировать все каналы из базы
/help - Помощь
            """
            await event.reply(menu_text)
        
        @self.bot_client.on(events.NewMessage(pattern='/analyze'))
        async def analyze_handler(event):
            """Анализ одного канала"""
            if not self.user_client:
                await event.reply("❌ Ошибка: пользовательская сессия не найдена!")
                return
            
            try:
                parts = event.text.split()
                if len(parts) < 2:
                    await event.reply("❌ Использование: /analyze @channelname")
                    return
                
                channel_input = parts[1].replace('@', '')
                await event.reply(f"🔍 Анализирую @{channel_input}...")
                
                # Анализируем канал
                result = await self.analyze_channel(channel_input)
                
                if result:
                    response = f"""
📊 **Анализ канала:** @{channel_input}

📢 **Название:** {result['title']}
👥 **Участники:** {result['participants_count']}
📁 **Файлы:** {result['files_count']}
🎤 **Голосовые:** {result['voices_count']}
📅 **Сообщений всего:** {result['total_messages']}
🕒 **Проверено:** {result['checked_time']}
                    """
                else:
                    response = f"❌ Не удалось проанализировать @{channel_input}"
                
                await event.reply(response)
                
            except Exception as e:
                await event.reply(f"❌ Ошибка: {e}")
        
        @self.bot_client.on(events.NewMessage(pattern='/add_channel'))
        async def add_channel_handler(event):
            """Добавить канал в базу"""
            try:
                parts = event.text.split()
                if len(parts) < 2:
                    await event.reply("❌ Использование: /add_channel @channelname")
                    return
                
                channel_input = parts[1].replace('@', '')
                
                # Сохраняем в базу
                self.cursor.execute(
                    'INSERT OR IGNORE INTO channels (username, last_checked) VALUES (?, ?)',
                    (channel_input, time.time())
                )
                self.conn.commit()
                
                await event.reply(f"✅ Канал @{channel_input} добавлен в базу")
                
            except Exception as e:
                await event.reply(f"❌ Ошибка: {e}")
        
        @self.bot_client.on(events.NewMessage(pattern='/list_channels'))
        async def list_channels_handler(event):
            """Список каналов в базе"""
            channels = self.get_channels()
            if not channels:
                await event.reply("❌ В базе нет каналов")
                return
            
            text = "📋 **Каналы в базе:**\n\n"
            for i, channel in enumerate(channels, 1):
                status = "✅" if channel[4] else "❌"
                text += f"{i}. {status} @{channel[1]}\n"
            
            await event.reply(text)
        
        @self.bot_client.on(events.NewMessage(pattern='/stats'))
        async def stats_handler(event):
            """Статистика всех каналов"""
            channels = self.get_channels_with_stats()
            if not channels:
                await event.reply("❌ Нет данных для статистики")
                return
            
            total_files = sum(channel[4] or 0 for channel in channels)
            total_voices = sum(channel[5] or 0 for channel in channels)
            total_participants = sum(channel[3] or 0 for channel in channels)
            
            text = f"""
📈 **Общая статистика:**

📊 Каналов в базе: {len(channels)}
📁 Всего файлов: {total_files}
🎤 Всего голосовых: {total_voices}
👥 Сумма участников: {total_participants}

**Топ каналов по файлам:**
"""
            
            # Сортируем по количеству файлов
            sorted_channels = sorted([c for c in channels if c[4]], key=lambda x: x[4], reverse=True)[:5]
            
            for i, channel in enumerate(sorted_channels, 1):
                text += f"{i}. @{channel[1]} - {channel[4]} файлов\n"
            
            await event.reply(text)
        
        @self.bot_client.on(events.NewMessage(pattern='/scan_all'))
        async def scan_all_handler(event):
            """Сканировать все каналы из базы"""
            if not self.user_client:
                await event.reply("❌ Ошибка: пользовательская сессия не найдена!")
                return
            
            channels = self.get_channels()
            if not channels:
                await event.reply("❌ В базе нет каналов")
                return
            
            await event.reply(f"🔄 Начинаю сканирование {len(channels)} каналов...")
            
            scanned = 0
            for channel in channels:
                try:
                    username = channel[1]
                    await event.reply(f"🔍 Сканирую @{username}...")
                    
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
                    
                    # Задержка чтобы не спамить
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Ошибка сканирования @{channel[1]}: {e}")
                    continue
            
            await event.reply(f"✅ Сканирование завершено! Обработано: {scanned}/{len(channels)} каналов")
    
    async def analyze_channel(self, username):
        """Анализ канала - подсчет файлов, голосовых и т.д."""
        try:
            # Получаем информацию о канале
            channel = await self.user_client.get_entity(username)
            
            files_count = 0
            voices_count = 0
            total_messages = 0
            
            # Анализируем последние сообщения (можно увеличить лимит)
            async for message in self.user_client.iter_messages(channel, limit=1000):
                total_messages += 1
                
                if message.media:
                    if isinstance(message.media, MessageMediaDocument):
                        document = message.media.document
                        if isinstance(document, Document):
                            # Считаем файлы
                            files_count += 1
                            
                            # Проверяем голосовые сообщения
                            if hasattr(document, 'mime_type') and document.mime_type == 'audio/ogg':
                                voices_count += 1
            
            # Получаем количество участников (если канал публичный)
            participants_count = 0
            try:
                participants = await self.user_client.get_participants(channel)
                participants_count = len(participants)
            except:
                # Если нельзя получить участников, используем приблизительное число
                participants_count = getattr(channel, 'participants_count', 0)
            
            return {
                'title': getattr(channel, 'title', 'Неизвестно'),
                'participants_count': participants_count,
                'files_count': files_count,
                'voices_count': voices_count,
                'total_messages': total_messages,
                'checked_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"Ошибка анализа канала @{username}: {e}")
            return None
    
    def get_channels(self):
        """Получить список каналов"""
        self.cursor.execute('SELECT * FROM channels')
        return self.cursor.fetchall()
    
    def get_channels_with_stats(self):
        """Получить каналы со статистикой"""
        self.cursor.execute('SELECT * FROM channels WHERE files_count IS NOT NULL')
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
        logger.info("Channel Analyzer Bot запущен")
        await self.bot_client.run_until_disconnected()

# Запуск бота
if __name__ == '__main__':
    bot = ChannelAnalyzerBot()
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        if hasattr(bot, 'conn'):
            bot.conn.close()
