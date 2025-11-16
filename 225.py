import asyncio
import logging
from telethon import TelegramClient, events, types
import signal
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
API_ID = 29385016    # ваши данные с my.telegram.org
API_HASH = "3c57df8805ab5de5a23a032ed39b9af9"  # ваши данные с my.telegram.org
BOT_TOKEN = "8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk"  # токен бота от @BotFather

# Целевые каналы для мониторинга
SOURCE_CHANNELS = ["NanaDoza", "test2"]  # каналы откуда брать посты
DESTINATION_CHANNEL = "https://t.me/+o7n5Ad6yZbo4Njcy"  # канал куда отправлять

class TelegramMonitor:
    def __init__(self):
        self.monitoring = False
        self.source_channels = SOURCE_CHANNELS.copy()
        self.destination_channel = DESTINATION_CHANNEL
        self.client = None
        self.bot = None
        
    async def initialize(self):
        """Инициализация клиентов"""
        try:
            self.client = TelegramClient("user_session", API_ID, API_HASH)
            self.bot = TelegramClient("bot_session", API_ID, API_HASH)
            
            await self.client.start()
            await self.bot.start(bot_token=BOT_TOKEN)
            
            # Проверяем авторизацию
            me = await self.client.get_me()
            bot_me = await self.bot.get_me()
            
            logger.info(f"Клиент авторизован как: {me.first_name}")
            logger.info(f"Бот авторизован как: {bot_me.first_name}")
            
            return True
        except Exception as e:
            logger.error(f"Ошибка инициализации: {e}")
            return False
    
    async def start_monitoring(self):
        """Запуск мониторинга каналов"""
        if self.monitoring:
            logger.warning("Мониторинг уже запущен")
            return
        
        self.monitoring = True
        logger.info("Мониторинг каналов запущен")
        
        @self.client.on(events.NewMessage(chats=self.source_channels))
        async def message_handler(event):
            if isinstance(event.chat, types.Channel) and self.monitoring:
                try:
                    username = event.chat.username
                    channel_info = f"📢 Пост из канала: @{username}" if username else f"📢 Пост из канала: {event.chat.title}"
                    
                    # Создаем инлайн-кнопки
                    buttons = [
                        [types.KeyboardButtonUrl("🔗 Источник", f"https://t.me/{username}")] if username else [],
                        [types.KeyboardButtonCallback("⏸️ Приостановить", b"pause_monitoring")]
                    ]
                    
                    # Отправляем информацию о канале
                    await self.client.send_message(
                        self.destination_channel, 
                        channel_info,
                        buttons=buttons
                    )
                    
                    # Отправляем сам пост
                    await self.client.send_message(
                        self.destination_channel, 
                        event.message
                    )
                    
                    logger.info(f"Пост из {username or event.chat.title} отправлен")
                    
                except Exception as e:
                    logger.error(f"Ошибка при отправке поста: {e}")
    
    async def stop_monitoring(self):
        """Остановка мониторинга"""
        self.monitoring = False
        if self.client:
            self.client.remove_event_handlers()
        logger.info("Мониторинг каналов остановлен")
    
    async def add_channel(self, channel_username):
        """Добавление канала для мониторинга"""
        if channel_username not in self.source_channels:
            self.source_channels.append(channel_username)
            await self.stop_monitoring()
            await self.start_monitoring()
            return True
        return False
    
    async def remove_channel(self, channel_username):
        """Удаление канала из мониторинга"""
        if channel_username in self.source_channels:
            self.source_channels.remove(channel_username)
            await self.stop_monitoring()
            await self.start_monitoring()
            return True
        return False
    
    def setup_bot_handlers(self):
        """Настройка обработчиков бота"""
        
        @self.bot.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            """Обработчик команды /start"""
            user = await event.get_sender()
            
            buttons = [
                [types.KeyboardButtonCallback("▶️ Запустить мониторинг", b"start_monitoring")],
                [types.KeyboardButtonCallback("⏸️ Приостановить", b"pause_monitoring")],
                [types.KeyboardButtonCallback("📊 Статус", b"show_status")],
                [types.KeyboardButtonCallback("📋 Список каналов", b"list_channels")]
            ]
            
            await event.reply(
                f"👋 Привет, {user.first_name}!\n\n"
                "Я бот для автоматической пересылки постов из каналов.\n\n"
                "Используйте кнопки ниже для управления:",
                buttons=buttons
            )
        
        @self.bot.on(events.NewMessage(pattern='/monitor'))
        async def monitor_handler(event):
            """Запуск мониторинга"""
            if not self.monitoring:
                await event.reply("🔄 Запускаю мониторинг каналов...")
                await self.start_monitoring()
            else:
                await event.reply("⚠️ Мониторинг уже запущен!")
        
        @self.bot.on(events.NewMessage(pattern='/pause'))
        async def pause_handler(event):
            """Приостановка мониторинга"""
            if self.monitoring:
                await self.stop_monitoring()
                await event.reply("⏸️ Мониторинг приостановлен")
            else:
                await event.reply("⚠️ Мониторинг уже остановлен!")
        
        @self.bot.on(events.NewMessage(pattern='/status'))
        async def status_handler(event):
            """Показать статус системы"""
            status = "🟢 Активен" if self.monitoring else "🔴 Остановлен"
            channels_count = len(self.source_channels)
            
            await event.reply(
                f"📊 **Статус системы:**\n\n"
                f"**Мониторинг:** {status}\n"
                f"**Каналов в мониторинге:** {channels_count}\n"
                f"**Целевой канал:** {self.destination_channel}"
            )
        
        @self.bot.on(events.NewMessage(pattern='/channels'))
        async def channels_handler(event):
            """Показать список каналов"""
            if self.source_channels:
                channels_list = "\n".join([f"• {channel}" for channel in self.source_channels])
                
                buttons = [
                    [types.KeyboardButtonCallback("➕ Добавить канал", b"add_channel")],
                    [types.KeyboardButtonCallback("➖ Удалить канал", b"remove_channel")]
                ]
                
                await event.reply(
                    f"📋 **Каналы в мониторинге:**\n\n{channels_list}",
                    buttons=buttons
                )
            else:
                await event.reply("📭 Список каналов пуст")
        
        # Обработчики инлайн-кнопок
        @self.bot.on(events.CallbackQuery)
        async def callback_handler(event):
            """Обработчик нажатий на инлайн-кнопки"""
            data = event.data.decode('utf-8')
            
            if data == "start_monitoring":
                if not self.monitoring:
                    await event.edit("🔄 Запускаю мониторинг каналов...")
                    await self.start_monitoring()
                    await event.answer("Мониторинг запущен!")
                else:
                    await event.answer("⚠️ Мониторинг уже запущен!", alert=True)
                    
            elif data == "pause_monitoring":
                if self.monitoring:
                    await self.stop_monitoring()
                    await event.edit("⏸️ Мониторинг приостановлен")
                    await event.answer("Мониторинг остановлен!")
                else:
                    await event.answer("⚠️ Мониторинг уже остановлен!", alert=True)
                    
            elif data == "show_status":
                status = "🟢 Активен" if self.monitoring else "🔴 Остановлен"
                channels_count = len(self.source_channels)
                
                await event.edit(
                    f"📊 **Статус системы:**\n\n"
                    f"**Мониторинг:** {status}\n"
                    f"**Каналов в мониторинге:** {channels_count}\n"
                    f"**Целевой канал:** {self.destination_channel}"
                )
                
            elif data == "list_channels":
                if self.source_channels:
                    channels_list = "\n".join([f"• {channel}" for channel in self.source_channels])
                    await event.edit(f"📋 **Каналы в мониторинге:**\n\n{channels_list}")
                else:
                    await event.edit("📭 Список каналов пуст")
            
            elif data == "add_channel":
                await event.answer("Используйте команду /add_channel в чате", alert=True)
            
            elif data == "remove_channel":
                await event.answer("Используйте команду /remove_channel в чате", alert=True)
    
    async def cleanup(self):
        """Корректное завершение работы"""
        logger.info("Завершение работы...")
        await self.stop_monitoring()
        if self.client:
            await self.client.disconnect()
        if self.bot:
            await self.bot.disconnect()
        logger.info("Работа завершена")

# Глобальные переменные для обработки сигналов
monitor = TelegramMonitor()

def signal_handler(signum, frame):
    """Обработчик сигналов завершения"""
    logger.info(f"Получен сигнал {signum}, завершаем работу...")
    asyncio.create_task(monitor.cleanup())
    sys.exit(0)

async def main():
    """Основная функция запуска"""
    try:
        # Регистрируем обработчики сигналов
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Инициализация
        if not await monitor.initialize():
            logger.error("Не удалось инициализировать клиенты")
            return
        
        # Настраиваем обработчики бота
        monitor.setup_bot_handlers()
        
        logger.info("Бот запущен и готов к работе")
        logger.info(f"Мониторинг каналов: {monitor.source_channels}")
        logger.info(f"Целевой канал: {monitor.destination_channel}")
        
        # Запускаем бота
        await monitor.bot.run_until_disconnected()
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await monitor.cleanup()

if __name__ == "__main__":
    # Устанавливаем политику event loop для Windows (если нужно)
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Запускаем основную функцию
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")
