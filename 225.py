# bot_pythonanywhere.py
import asyncio
import logging
from telethon import TelegramClient, events

# Настройка для PythonAnywhere
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramCheckerBot:
    def __init__(self):
        self.API_ID = '29385016'
        self.API_HASH = '3c57df8805ab5de5a23a032ed39b9af9'
        self.BOT_TOKEN = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'

        self.user_client = None
        self.bot_client = None

    async def initialize(self):
        """Инициализация клиентов"""
        self.user_client = TelegramClient('session_user', self.API_ID, self.API_HASH)
        self.bot_client = TelegramClient('session_bot', self.API_ID, self.API_HASH)

        await self.user_client.start()
        await self.bot_client.start(bot_token=self.BOT_TOKEN)

        self.setup_handlers()
        logger.info("Бот инициализирован")

    def setup_handlers(self):
        """Настройка обработчиков событий"""

        @self.bot_client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            await event.reply("🤖 Бот запущен! Отправь мне username для проверки.")

        @self.bot_client.on(events.NewMessage(pattern='/check'))
        async def check_handler(event):
            try:
                text = event.text.split()
                if len(text) < 2:
                    await event.reply("Укажите username: /check @username")
                    return

                username = text[1].replace('@', '')
                result = await self.check_user_exists(username)

                if result['exists']:
                    response = f"✅ @{username} существует\nID: {result['id']}"
                else:
                    response = f"❌ @{username} не существует"

                await event.reply(response)

            except Exception as e:
                await event.reply(f"❌ Ошибка: {e}")

        @self.bot_client.on(events.NewMessage)
        async def message_handler(event):
            text = event.text.strip()
            if text.startswith('/'):
                return

            if len(text) <= 32 and not ' ' in text:
                username = text.replace('@', '')
                result = await self.check_user_exists(username)

                if result['exists']:
                    response = f"✅ @{username} существует\nID: {result['id']}"
                else:
                    response = f"❌ @{username} не существует"

                await event.reply(response)

    async def check_user_exists(self, username):
        """Проверка существования пользователя"""
        try:
            user = await self.user_client.get_entity(username)
            return {
                'exists': True,
                'id': user.id,
                'first_name': user.first_name
            }
        except Exception:
            return {'exists': False}

    async def run(self):
        """Запуск бота"""
        await self.initialize()
        logger.info("Бот запущен и готов к работе")
        await self.bot_client.run_until_disconnected()

# Создаем и запускаем бота
bot = TelegramCheckerBot()

# Для PythonAnywhere используем этот вызов
if __name__ == '__main__':
    asyncio.run(bot.run())
