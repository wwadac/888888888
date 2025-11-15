import asyncio
import logging
from telethon import TelegramClient, events

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramCheckerBot:
    def __init__(self):
        self.API_ID = '29385016'
        self.API_HASH = '3c57df8805ab5de5a23a032ed39b9af9'
        self.BOT_TOKEN = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'  # Получи у @BotFather
        
        self.bot_client = None
    
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
        """Настройка обработчиков событий"""
        
        @self.bot_client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            welcome_text = """
🤖 **User Checker Bot**

Я могу проверить существование пользователя Telegram по username.

**Команды:**
/check @username - Проверить пользователя
/bulk user1,user2,user3 - Проверить несколько
/help - Помощь

Просто отправь мне username с @ или без!
            """
            await event.reply(welcome_text)
        
        @self.bot_client.on(events.NewMessage(pattern='/help'))
        async def help_handler(event):
            help_text = """
📖 **Помощь**

**Как использовать:**
1. Отправь username: `@username` или просто `username`
2. Используй команду: `/check @username`
3. Для нескольких: `/bulk user1,user2,user3`

**Примеры:**
• `@durov`
• `/check @durov` 
• `/bulk durov, telegram, news`
            """
            await event.reply(help_text)
        
        @self.bot_client.on(events.NewMessage(pattern='/check'))
        async def check_handler(event):
            try:
                text = event.text.split()
                if len(text) < 2:
                    await event.reply("❌ Укажите username после команды:\n`/check @username`")
                    return
                
                username = text[1].replace('@', '')
                await self.process_check(event, username)
                
            except Exception as e:
                logger.error(f"Error in check_handler: {e}")
                await event.reply("❌ Произошла ошибка при обработке запроса")
        
        @self.bot_client.on(events.NewMessage(pattern='/bulk'))
        async def bulk_handler(event):
            try:
                text = event.text.split(maxsplit=1)
                if len(text) < 2:
                    await event.reply("❌ Укажите usernames через запятую:\n`/bulk user1,user2,user3`")
                    return
                
                usernames_text = text[1]
                usernames = [u.strip().replace('@', '') for u in usernames_text.split(',')]
                
                if len(usernames) > 10:
                    await event.reply("❌ Максимум 10 пользователей за раз")
                    return
                
                await event.reply(f"🔍 Проверяю {len(usernames)} пользователей...")
                
                results = []
                for username in usernames:
                    if username:
                        try:
                            user = await self.bot_client.get_entity(username)
                            results.append(f"✅ @{username} - существует (ID: {user.id})")
                        except:
                            results.append(f"❌ @{username} - не существует")
                
                response = "**Результаты проверки:**\n" + "\n".join(results)
                await event.reply(response)
                
            except Exception as e:
                logger.error(f"Error in bulk_handler: {e}")
                await event.reply("❌ Произошла ошибка при массовой проверке")
        
        @self.bot_client.on(events.NewMessage)
        async def message_handler(event):
            try:
                text = event.text.strip()
                
                # Игнорируем команды
                if text.startswith('/'):
                    return
                    
                # Проверяем, похоже ли на username
                if len(text) <= 32 and (text.startswith('@') or not ' ' in text):
                    username = text.replace('@', '')
                    await self.process_check(event, username)
                else:
                    await event.reply("❌ Отправьте username для проверки (например: `@username` или `username`)")
                    
            except Exception as e:
                logger.error(f"Error in message_handler: {e}")
                await event.reply("❌ Произошла ошибка при обработке запроса")
    
    async def process_check(self, event, username):
        """Обрабатывает проверку username"""
        if not username:
            await event.reply("❌ Укажите username для проверки")
            return
        
        # Проверяем длину username
        if len(username) > 32:
            await event.reply("❌ Слишком длинный username")
            return
        
        await event.reply(f"🔍 Проверяю @{username}...")
        
        try:
            user = await self.bot_client.get_entity(username)
            
            user_type = "🤖 Бот" if user.bot else "👤 Пользователь"
            response = f"""
✅ **Пользователь существует!**

**ID:** `{user.id}`
**Имя:** {user.first_name or 'Не указано'}
**Фамилия:** {user.last_name or 'Не указана'}
**Username:** @{user.username or 'Не указан'}
**Тип:** {user_type}
            """
            
        except Exception as e:
            response = f"❌ Пользователь **@{username}** не существует или аккаунт приватный"
            logger.error(f"Error checking @{username}: {e}")
        
        await event.reply(response)
    
    async def run(self):
        """Запуск бота"""
        await self.initialize()
        logger.info("Бот запущен и готов к работе")
        await self.bot_client.run_until_disconnected()

# Создаем и запускаем бота
bot = TelegramCheckerBot()

if __name__ == '__main__':
    asyncio.run(bot.run())
