from telethon import TelegramClient, events, types, functions, sync
from telethon.tl.types import InputPeerChannel
import asyncio
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
API_ID = 29385016    # ваши данные с my.telegram.org
API_HASH = "3c57df8805ab5de5a23a032ed39b9af9"  # ваши данные с my.telegram.org
BOT_TOKEN = "8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk"  # токен бота от @BotFather

# Целевые каналы для мониторинга
SOURCE_CHANNELS = ["NanaDoza", "test2", "test3"]  # каналы откуда брать посты
DESTINATION_CHANNEL = "https://t.me/+o7n5Ad6yZbo4Njcy"  # канал куда отправлять

# Инициализация клиента
client = TelegramClient("user_session", API_ID, API_HASH)
bot = TelegramClient("bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

class ChannelMonitor:
    def __init__(self):
        self.monitoring = False
        self.source_channels = SOURCE_CHANNELS.copy()
        self.destination_channel = DESTINATION_CHANNEL
    
    async def start_monitoring(self):
        """Запуск мониторинга каналов"""
        self.monitoring = True
        logger.info("Мониторинг каналов запущен")
        
        @client.on(events.NewMessage(chats=self.source_channels))
        async def message_handler(event):
            if isinstance(event.chat, types.Channel) and self.monitoring:
                try:
                    username = event.chat.username
                    channel_info = f"📢 Пост из канала: @{username}" if username else f"📢 Пост из канала: {event.chat.title}"
                    
                    # Создаем инлайн-кнопки
                    buttons = [
                        [types.KeyboardButtonUrl("🔗 Источник", f"https://t.me/{username}")] if username else [],
                        [types.KeyboardButtonCallback("⏸️ Приостановить", b"pause_monitoring")],
                        [types.KeyboardButtonCallback("📊 Статус", b"show_status")]
                    ]
                    
                    # Отправляем информацию о канале
                    await client.send_message(
                        self.destination_channel, 
                        channel_info,
                        buttons=buttons
                    )
                    
                    # Отправляем сам пост
                    await client.send_message(
                        self.destination_channel, 
                        event.message
                    )
                    
                    logger.info(f"Пост из {username or event.chat.title} отправлен")
                    
                except Exception as e:
                    logger.error(f"Ошибка при отправке поста: {e}")
        
        await client.run_until_disconnected()
    
    async def stop_monitoring(self):
        """Остановка мониторинга"""
        self.monitoring = False
        client.remove_event_handlers()
        logger.info("Мониторинг каналов остановлен")
    
    async def add_channel(self, channel_username):
        """Добавление канала для мониторинга"""
        if channel_username not in self.source_channels:
            self.source_channels.append(channel_username)
            return True
        return False
    
    async def remove_channel(self, channel_username):
        """Удаление канала из мониторинга"""
        if channel_username in self.source_channels:
            self.source_channels.remove(channel_username)
            return True
        return False

# Создаем экземпляр монитора
monitor = ChannelMonitor()

# Обработчики команд бота
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """Обработчик команды /start"""
    user = await event.get_sender()
    
    buttons = [
        [types.KeyboardButtonCallback("▶️ Запустить мониторинг", b"start_monitoring")],
        [types.KeyboardButtonCallback("⏸️ Приостановить", b"pause_monitoring")],
        [types.KeyboardButtonCallback("📊 Статус", b"show_status")],
        [types.KeyboardButtonCallback("📋 Список каналов", b"list_channels")],
        [types.KeyboardButtonCallback("⚙️ Настройки", b"settings")]
    ]
    
    await event.reply(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я бот для автоматической пересылки постов из каналов.\n\n"
        "Доступные команды:\n"
        "▶️ /start - Запустить бота\n"
        "▶️ /monitor - Начать мониторинг\n"
        "⏸️ /pause - Приостановить\n"
        "📊 /status - Статус системы\n"
        "📋 /channels - Список каналов\n"
        "➕ /add_channel - Добавить канал\n"
        "➖ /remove_channel - Удалить канал\n"
        "⚙️ /settings - Настройки",
        buttons=buttons
    )

@bot.on(events.NewMessage(pattern='/monitor'))
async def monitor_handler(event):
    """Запуск мониторинга"""
    if not monitor.monitoring:
        await event.reply("🔄 Запускаю мониторинг каналов...")
        asyncio.create_task(monitor.start_monitoring())
    else:
        await event.reply("⚠️ Мониторинг уже запущен!")

@bot.on(events.NewMessage(pattern='/pause'))
async def pause_handler(event):
    """Приостановка мониторинга"""
    if monitor.monitoring:
        await monitor.stop_monitoring()
        await event.reply("⏸️ Мониторинг приостановлен")
    else:
        await event.reply("⚠️ Мониторинг уже остановлен!")

@bot.on(events.NewMessage(pattern='/status'))
async def status_handler(event):
    """Показать статус системы"""
    status = "🟢 Активен" if monitor.monitoring else "🔴 Остановлен"
    channels_count = len(monitor.source_channels)
    
    await event.reply(
        f"📊 **Статус системы:**\n\n"
        f"**Мониторинг:** {status}\n"
        f"**Каналов в мониторинге:** {channels_count}\n"
        f"**Целевой канал:** {monitor.destination_channel}"
    )

@bot.on(events.NewMessage(pattern='/channels'))
async def channels_handler(event):
    """Показать список каналов"""
    if monitor.source_channels:
        channels_list = "\n".join([f"• {channel}" for channel in monitor.source_channels])
        
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

@bot.on(events.NewMessage(pattern='/add_channel'))
async def add_channel_handler(event):
    """Добавить канал в мониторинг"""
    try:
        # Просим пользователя ввести username канала
        async with bot.conversation(event.chat_id) as conv:
            await conv.send_message("Введите username канала (например: @channel_name):")
            response = await conv.get_response()
            channel_username = response.text.strip().replace('@', '')
            
            if await monitor.add_channel(channel_username):
                await conv.send_message(f"✅ Канал @{channel_username} добавлен в мониторинг")
            else:
                await conv.send_message(f"⚠️ Канал @{channel_username} уже в списке мониторинга")
                
    except Exception as e:
        await event.reply(f"❌ Ошибка при добавлении канала: {e}")

@bot.on(events.NewMessage(pattern='/remove_channel'))
async def remove_channel_handler(event):
    """Удалить канал из мониторинга"""
    try:
        async with bot.conversation(event.chat_id) as conv:
            await conv.send_message("Введите username канала для удаления:")
            response = await conv.get_response()
            channel_username = response.text.strip().replace('@', '')
            
            if await monitor.remove_channel(channel_username):
                await conv.send_message(f"✅ Канал @{channel_username} удален из мониторинга")
            else:
                await conv.send_message(f"⚠️ Канал @{channel_username} не найден в списке мониторинга")
                
    except Exception as e:
        await event.reply(f"❌ Ошибка при удалении канала: {e}")

@bot.on(events.NewMessage(pattern='/settings'))
async def settings_handler(event):
    """Настройки бота"""
    buttons = [
        [types.KeyboardButtonCallback("📝 Изменить целевой канал", b"change_dest")],
        [types.KeyboardButtonCallback("📋 Список каналов", b"list_channels")],
        [types.KeyboardButtonCallback("🔄 Сбросить настройки", b"reset_settings")],
        [types.KeyboardButtonCallback("↩️ Назад", b"main_menu")]
    ]
    
    await event.reply(
        "⚙️ **Настройки бота:**\n\n"
        "Здесь вы можете настроить параметры работы бота.",
        buttons=buttons
    )

# Обработчики инлайн-кнопок
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    """Обработчик нажатий на инлайн-кнопки"""
    data = event.data.decode('utf-8')
    chat = await event.get_chat()
    
    if data == "start_monitoring":
        if not monitor.monitoring:
            await event.edit("🔄 Запускаю мониторинг каналов...")
            asyncio.create_task(monitor.start_monitoring())
        else:
            await event.answer("⚠️ Мониторинг уже запущен!", alert=True)
            
    elif data == "pause_monitoring":
        if monitor.monitoring:
            await monitor.stop_monitoring()
            await event.edit("⏸️ Мониторинг приостановлен")
        else:
            await event.answer("⚠️ Мониторинг уже остановлен!", alert=True)
            
    elif data == "show_status":
        status = "🟢 Активен" if monitor.monitoring else "🔴 Остановлен"
        channels_count = len(monitor.source_channels)
        
        await event.edit(
            f"📊 **Статус системы:**\n\n"
            f"**Мониторинг:** {status}\n"
            f"**Каналов в мониторинге:** {channels_count}\n"
            f"**Целевой канал:** {monitor.destination_channel}"
        )
        
    elif data == "list_channels":
        if monitor.source_channels:
            channels_list = "\n".join([f"• {channel}" for channel in monitor.source_channels])
            await event.edit(f"📋 **Каналы в мониторинге:**\n\n{channels_list}")
        else:
            await event.edit("📭 Список каналов пуст")
            
    elif data == "main_menu":
        await event.edit(
            "🏠 **Главное меню:**\n\n"
            "Выберите действие:",
            buttons=[
                [types.KeyboardButtonCallback("▶️ Запустить мониторинг", b"start_monitoring")],
                [types.KeyboardButtonCallback("⏸️ Приостановить", b"pause_monitoring")],
                [types.KeyboardButtonCallback("📊 Статус", b"show_status")],
                [types.KeyboardButtonCallback("📋 Список каналов", b"list_channels")],
                [types.KeyboardButtonCallback("⚙️ Настройки", b"settings")]
            ]
        )

async def main():
    """Основная функция запуска"""
    logger.info("Запуск бота и клиента...")
    await client.start()
    await bot.start()
    
    # Проверяем авторизацию
    me = await client.get_me()
    bot_me = await bot.get_me()
    
    logger.info(f"Клиент авторизован как: {me.first_name}")
    logger.info(f"Бот авторизован как: {bot_me.first_name}")
    logger.info(f"Мониторинг каналов: {monitor.source_channels}")
    logger.info(f"Целевой канал: {monitor.destination_channel}")
    
    await bot.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
