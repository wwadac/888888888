import asyncio
import logging
import sqlite3
import time
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.tl.types import (
    Document, Photo, DocumentVideo, DocumentAudio, 
    MessageMediaDocument, MessageMediaPhoto
)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChannelForwardBot:
    def __init__(self):
        self.API_ID = '29385016'  # Ваш API ID
        self.API_HASH = '3c57df8805ab5de5a23a032ed39b9af9'  # Ваш API HASH
        self.BOT_TOKEN = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'  # Токен бота
        
        self.client = None
        self.bot_client = None
        self.setup_database()
        
        # Настройки по умолчанию
        self.forward_interval = 60  # Интервал в секундах
        self.is_running = False
        self.current_task = None
        
    def setup_database(self):
        """Настройка базы данных для хранения настроек"""
        self.conn = sqlite3.connect('forward_settings.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Таблица с настройками
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                id INTEGER PRIMARY KEY,
                source_channel TEXT,
                target_channel TEXT,
                forward_interval INTEGER DEFAULT 60,
                last_message_id INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 0
            )
        ''')
        
        # Таблица со статистикой
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                files_forwarded INTEGER,
                operation_time REAL
            )
        ''')
        
        # Инициализация настроек если их нет
        self.cursor.execute('SELECT COUNT(*) FROM bot_settings')
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute(
                'INSERT INTO bot_settings (id, forward_interval) VALUES (1, 60)'
            )
        
        self.conn.commit()
    
    def get_settings(self):
        """Получение текущих настроек"""
        self.cursor.execute('SELECT * FROM bot_settings WHERE id = 1')
        result = self.cursor.fetchone()
        if result:
            return {
                'source_channel': result[1],
                'target_channel': result[2],
                'forward_interval': result[3],
                'last_message_id': result[4],
                'is_active': bool(result[5])
            }
        return None
    
    def update_settings(self, source_channel=None, target_channel=None, interval=None, last_message_id=None, is_active=None):
        """Обновление настроек"""
        settings = self.get_settings()
        if not settings:
            return
        
        source = source_channel if source_channel is not None else settings['source_channel']
        target = target_channel if target_channel is not None else settings['target_channel']
        interval_val = interval if interval is not None else settings['forward_interval']
        last_msg = last_message_id if last_message_id is not None else settings['last_message_id']
        active = is_active if is_active is not None else settings['is_active']
        
        self.cursor.execute('''
            UPDATE bot_settings 
            SET source_channel = ?, target_channel = ?, forward_interval = ?, last_message_id = ?, is_active = ?
            WHERE id = 1
        ''', (source, target, interval_val, last_msg, int(active)))
        self.conn.commit()
    
    async def initialize(self):
        """Инициализация клиентов"""
        # Клиент для вашего аккаунта
        self.client = TelegramClient('user_session', self.API_ID, self.API_HASH)
        await self.client.start()
        
        # Клиент для бота
        self.bot_client = TelegramClient('bot_session', self.API_ID, self.API_HASH)
        await self.bot_client.start(bot_token=self.BOT_TOKEN)
        
        self.setup_handlers()
        logger.info("Клиенты инициализированы")
    
    def setup_handlers(self):
        """Настройка обработчиков для бота"""
        
        @self.bot_client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            """Главное меню"""
            user_id = event.sender_id
            if not await self.is_admin(user_id):
                await event.reply("❌ **Доступ запрещен!**\n\nВы не являетесь администратором.")
                return
            
            settings = self.get_settings()
            status = "🟢 **АКТИВЕН**" if self.is_running else "🔴 **ОСТАНОВЛЕН**"
            
            text = f"""
🤖 **Админ-панель бота пересылки**

📊 **Статус:** {status}
🔄 **Интервал:** {settings['forward_interval']} секунд

📥 **Источник:** `{settings['source_channel'] or 'Не установлен'}`
📤 **Цель:** `{settings['target_channel'] or 'Не установлен'}`

⚡ **Доступные команды:**
            """
            
            buttons = [
                [Button.inline("📊 Статистика канала", b"channel_stats"),
                 Button.inline("⚙️ Настройки", b"settings")],
                [Button.inline("▶️ Старт", b"start_forward"),
                 Button.inline("⏹️ Стоп", b"stop_forward")],
                [Button.inline("🔄 Обновить", b"refresh")]
            ]
            
            await event.reply(text, buttons=buttons, parse_mode='md')
        
        @self.bot_client.on(events.CallbackQuery)
        async def callback_handler(event):
            """Обработчик callback кнопок"""
            user_id = event.sender_id
            if not await self.is_admin(user_id):
                await event.answer("❌ Доступ запрещен!", alert=True)
                return
            
            data = event.data.decode('utf-8')
            settings = self.get_settings()
            
            if data == "channel_stats":
                if not settings['source_channel']:
                    await event.answer("❌ Канал-источник не установлен!", alert=True)
                    return
                
                await event.answer("🔄 Получаем статистику...", alert=False)
                stats = await self.get_channel_stats(settings['source_channel'])
                await event.edit(stats, parse_mode='md')
                
            elif data == "settings":
                await self.show_settings(event)
                
            elif data == "start_forward":
                if not settings['source_channel'] or not settings['target_channel']:
                    await event.answer("❌ Сначала настройте каналы!", alert=True)
                    return
                
                if self.is_running:
                    await event.answer("⚠️ Бот уже работает!", alert=True)
                    return
                
                await self.start_forwarding()
                await event.answer("✅ Пересылка запущена!", alert=True)
                await start_handler(event)
                
            elif data == "stop_forward":
                if not self.is_running:
                    await event.answer("⚠️ Бот уже остановлен!", alert=True)
                    return
                
                await self.stop_forwarding()
                await event.answer("⏹️ Пересылка остановлена!", alert=True)
                await start_handler(event)
                
            elif data == "refresh":
                await start_handler(event)
                
            elif data == "set_source":
                await event.edit(
                    "📥 **Установка канала-источника**\n\n"
                    "Отправьте username или ID канала:\n\n"
                    "💡 **Примеры:**\n"
                    "• `@channel_username`\n"
                    "• `-1001234567890`\n\n"
                    "⚠️ **Ваш аккаунт должен быть подписан на канал!**",
                    parse_mode='md'
                )
                
            elif data == "set_target":
                await event.edit(
                    "📤 **Установка канала-цели**\n\n"
                    "Отправьте username или ID канала:\n\n"
                    "💡 **Примеры:**\n"
                    "• `@channel_username`\n"
                    "• `-1001234567890`\n\n"
                    "⚠️ **Бот должен быть админом в целевом канале!**",
                    parse_mode='md'
                )
                
            elif data.startswith("interval_"):
                interval = int(data.split("_")[1])
                self.update_settings(interval=interval)
                await event.answer(f"✅ Интервал установлен: {interval} сек", alert=True)
                await self.show_settings(event)
    
    async def show_settings(self, event):
        """Показать настройки"""
        settings = self.get_settings()
        
        text = f"""
⚙️ **Настройки бота**

📥 **Канал-источник:** `{settings['source_channel'] or 'Не установлен'}`
📤 **Канал-цель:** `{settings['target_channel'] or 'Не установлен'}`
🔄 **Интервал:** {settings['forward_interval']} секунд

📋 **Выберите действие:**
        """
        
        buttons = [
            [Button.inline("📥 Установить источник", b"set_source")],
            [Button.inline("📤 Установить цель", b"set_target")],
            [Button.inline("🔄 Интервал: 30 сек", b"interval_30"),
             Button.inline("🔄 Интервал: 60 сек", b"interval_60")],
            [Button.inline("🔄 Интервал: 120 сек", b"interval_120"),
             Button.inline("🔄 Интервал: 300 сек", b"interval_300")],
            [Button.inline("🔙 Назад", b"refresh")]
        ]
        
        await event.edit(text, buttons=buttons, parse_mode='md')
    
    async def is_admin(self, user_id):
        """Проверка, является ли пользователь администратором"""
        # Добавьте сюда ID администраторов
        admins = [123456789, 987654321]  # Замените на реальные ID
        return user_id in admins
    
    async def get_channel_stats(self, channel_identifier):
        """Получение статистики канала"""
        try:
            channel = await self.client.get_entity(channel_identifier)
            total_files = 0
            total_messages = 0
            
            async for message in self.client.iter_messages(channel):
                total_messages += 1
                if message.media:
                    if (isinstance(message.media, (MessageMediaDocument, MessageMediaPhoto)) or 
                        hasattr(message.media, 'document') or 
                        hasattr(message.media, 'photo')):
                        total_files += 1
            
            return f"""
📊 **Статистика канала:** `{channel_identifier}`

📨 **Всего сообщений:** `{total_messages}`
📎 **Всего файлов:** `{total_files}`
👥 **Участников:** `{getattr(channel, 'participants_count', 'N/A')}`

💡 **Информация:**
• Файлами считаются: документы, фото, видео, аудио
• Статистика обновлена: `{datetime.now().strftime('%H:%M:%S')}`
            """
            
        except Exception as e:
            logger.error(f"Error getting channel stats: {e}")
            return f"❌ **Ошибка:** Не удалось получить статистику канала `{channel_identifier}`"
    
    async def process_channel_input(self, event, is_source=True):
        """Обработка ввода канала"""
        try:
            text = event.text.strip()
            channel_identifier = text.replace('@', '')
            
            # Пробуем получить информацию о канале
            channel = await self.client.get_entity(channel_identifier)
            
            if is_source:
                self.update_settings(source_channel=channel_identifier)
                await event.reply(f"✅ **Канал-источник установлен!**\n\n`{channel_identifier}`")
            else:
                # Проверяем, что бот админ в целевом канале
                try:
                    await self.bot_client.get_permissions(channel_identifier, (await self.bot_client.get_me()).id)
                    self.update_settings(target_channel=channel_identifier)
                    await event.reply(f"✅ **Канал-цель установлен!**\n\n`{channel_identifier}`")
                except Exception:
                    await event.reply("❌ **Бот не является админом в целевом канале!**")
                    return
            
            # Показываем обновленные настройки
            await self.show_settings(event)
            
        except Exception as e:
            logger.error(f"Error setting channel: {e}")
            await event.reply("❌ **Ошибка!** Проверьте правильность ввода и права доступа.")
    
    async def start_forwarding(self):
        """Запуск пересылки"""
        if self.is_running:
            return
        
        self.is_running = True
        self.current_task = asyncio.create_task(self.forward_loop())
        logger.info("Forwarding started")
    
    async def stop_forwarding(self):
        """Остановка пересылки"""
        self.is_running = False
        if self.current_task:
            self.current_task.cancel()
            try:
                await self.current_task
            except asyncio.CancelledError:
                pass
        logger.info("Forwarding stopped")
    
    async def forward_loop(self):
        """Основной цикл пересылки"""
        while self.is_running:
            try:
                settings = self.get_settings()
                if not settings['source_channel'] or not settings['target_channel']:
                    await asyncio.sleep(10)
                    continue
                
                await self.forward_new_files()
                await asyncio.sleep(settings['forward_interval'])
                
            except Exception as e:
                logger.error(f"Error in forward loop: {e}")
                await asyncio.sleep(30)
    
    async def forward_new_files(self):
        """Пересылка новых файлов"""
        try:
            settings = self.get_settings()
            source_channel = await self.client.get_entity(settings['source_channel'])
            target_channel = await self.client.get_entity(settings['target_channel'])
            
            last_message_id = settings['last_message_id']
            new_last_message_id = last_message_id
            
            async for message in self.client.iter_messages(source_channel, min_id=last_message_id):
                if message.id > new_last_message_id:
                    new_last_message_id = message.id
                
                if message.media and message.id > last_message_id:
                    try:
                        # Пересылаем сообщение с медиа
                        await self.client.forward_messages(target_channel, message)
                        logger.info(f"Forwarded message {message.id}")
                        
                        # Обновляем last_message_id после успешной пересылки
                        self.update_settings(last_message_id=message.id)
                        
                        # Записываем статистику
                        self.cursor.execute(
                            'INSERT INTO statistics (date, files_forwarded, operation_time) VALUES (?, ?, ?)',
                            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 1, time.time())
                        )
                        self.conn.commit()
                        
                        # Ждем перед следующим сообщением
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Error forwarding message {message.id}: {e}")
            
            # Обновляем last_message_id если были новые сообщения
            if new_last_message_id > last_message_id:
                self.update_settings(last_message_id=new_last_message_id)
                
        except Exception as e:
            logger.error(f"Error in forward_new_files: {e}")
    
    async def run(self):
        """Запуск бота"""
        await self.initialize()
        
        # Обработчик для установки каналов
        @self.bot_client.on(events.NewMessage)
        async def message_handler(event):
            if event.text.startswith('/'):
                return
            
            settings = self.get_settings()
            if not settings['source_channel']:
                await self.process_channel_input(event, is_source=True)
            elif not settings['target_channel']:
                await self.process_channel_input(event, is_source=False)
        
        logger.info("🤖 Бот запущен и готов к работе!")
        logger.info("👨‍💼 Отправьте /start в боте для доступа к админ-панели")
        
        await self.bot_client.run_until_disconnected()

# Запуск бота
if __name__ == '__main__':
    bot = ChannelForwardBot()
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        if hasattr(bot, 'conn'):
            bot.conn.close()
