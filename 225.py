import asyncio
import logging
import sqlite3
from telethon import TelegramClient, events, Button
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramParserBot:
    def __init__(self):
        self.API_ID = '29385016'
        self.API_HASH = '3c57df8805ab5de5a23a032ed39b9af9'
        self.BOT_TOKEN = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'
        
        self.bot_client = None
        self.setup_database()
    
    def setup_database(self):
        """Настройка базы данных для хранения лимитов"""
        self.conn = sqlite3.connect('user_limits.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_requests (
                user_id INTEGER PRIMARY KEY,
                request_count INTEGER DEFAULT 0,
                last_reset_time REAL
            )
        ''')
        self.conn.commit()
    
    async def check_user_limit(self, user_id):
        """Проверяет лимит запросов для пользователя"""
        now = time.time()
        
        self.cursor.execute(
            'SELECT request_count, last_reset_time FROM user_requests WHERE user_id = ?',
            (user_id,)
        )
        result = self.cursor.fetchone()
        
        if not result:
            return True, 5
        
        request_count, last_reset_time = result
        
        if now - last_reset_time >= 2400:
            return True, 5
        else:
            if request_count >= 5:
                return False, 0
            else:
                return True, 5 - request_count
    
    async def increment_request_count(self, user_id):
        """Увеличивает счетчик запросов"""
        now = time.time()
        
        self.cursor.execute(
            'SELECT request_count, last_reset_time FROM user_requests WHERE user_id = ?',
            (user_id,)
        )
        result = self.cursor.fetchone()
        
        if not result:
            self.cursor.execute(
                'INSERT INTO user_requests (user_id, request_count, last_reset_time) VALUES (?, ?, ?)',
                (user_id, 1, now)
            )
        else:
            request_count, last_reset_time = result
            if now - last_reset_time >= 2400:
                self.cursor.execute(
                    'UPDATE user_requests SET request_count = 1, last_reset_time = ? WHERE user_id = ?',
                    (now, user_id)
                )
            else:
                self.cursor.execute(
                    'UPDATE user_requests SET request_count = request_count + 1 WHERE user_id = ?',
                    (user_id,)
                )
        
        self.conn.commit()
    
    async def get_remaining_time(self, user_id):
        """Получает оставшееся время до сброса"""
        self.cursor.execute(
            'SELECT last_reset_time FROM user_requests WHERE user_id = ?',
            (user_id,)
        )
        result = self.cursor.fetchone()
        
        if result:
            last_reset_time = result[0]
            elapsed = time.time() - last_reset_time
            remaining = max(0, 2400 - elapsed)
            return remaining
        return 0
    
    async def get_user_stats(self, user_id):
        """Получает статистику пользователя"""
        self.cursor.execute(
            'SELECT request_count, last_reset_time FROM user_requests WHERE user_id = ?',
            (user_id,)
        )
        result = self.cursor.fetchone()
        
        if result:
            request_count, last_reset_time = result
            remaining_time = await self.get_remaining_time(user_id)
            return {
                'used': request_count,
                'remaining': max(0, 5 - request_count),
                'remaining_time': remaining_time
            }
        return {'used': 0, 'remaining': 5, 'remaining_time': 0}
    
    async def initialize(self):
        """Инициализация бота"""
        self.bot_client = TelegramClient(
            'session_bot', 
            self.API_ID, 
            self.API_HASH
        )
        
        await self.bot_client.start(bot_token=self.BOT_TOKEN)
        self.setup_handlers()
        logger.info("Парсер бот инициализирован")
    
    def setup_handlers(self):
        """Настройка обработчиков событий"""
        
        @self.bot_client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            user_id = event.sender_id
            stats = await self.get_user_stats(user_id)
            
            welcome_text = f"""
🤖 Telegram Parser Bot

У вас {stats['remaining']}/5 запросов на парсинг

📋 Доступные команды:
/parse - Начать парсинг чата
/stats - Показать статистику
/help - Помощь

Отправьте ссылку на публичный чат для анализа
            """
            
            buttons = [
                [Button.inline("🔍 Начать парсинг", b"start_parsing")],
                [Button.inline("📊 Моя статистика", b"show_stats")]
            ]
            
            await event.reply(welcome_text, buttons=buttons)
        
        @self.bot_client.on(events.NewMessage(pattern='/stats'))
        async def stats_handler(event):
            user_id = event.sender_id
            stats = await self.get_user_stats(user_id)
            
            minutes_left = int(stats['remaining_time'] // 60)
            seconds_left = int(stats['remaining_time'] % 60)
            
            stats_text = f"""
📊 Статистика:

✅ Использовано: {stats['used']}/5
🔄 Осталось: {stats['remaining']}
⏰ Сброс через: {minutes_left}мин {seconds_left}сек
            """
            
            await event.reply(stats_text)
        
        @self.bot_client.on(events.NewMessage(pattern='/parse'))
        async def parse_handler(event):
            user_id = event.sender_id
            stats = await self.get_user_stats(user_id)
            
            if stats['remaining'] <= 0:
                minutes_left = int(stats['remaining_time'] // 60)
                await event.reply(f"❌ Лимит исчерпан! Подождите {minutes_left} минут")
                return
            
            parse_instructions = """
🔍 **Парсинг пользователей из чата**

Отправьте ссылку на публичный чат в формате:
- @username
- https://t.me/username
- https://t.me/joinchat/xxxxx

Бот соберет пользователей и сохранит в файл.
            """
            
            await event.reply(parse_instructions)
        
        @self.bot_client.on(events.NewMessage(pattern='/help'))
        async def help_handler(event):
            help_text = """
📖 **Помощь по использованию парсера**

1. Используйте /parse для начала парсинга
2. Отправьте ссылку на публичный чат
3. Бот соберет пользователей (50-100 человек)
4. Результат будет сохранен в TXT файл

⚠️ **Ограничения:**
- 5 запросов в сутки
- Только публичные чаты
- Минимальный размер чата: 50 участников

📝 **Примеры ссылок:**
@telegram
https://t.me/telegram
https://t.me/joinchat/AAAAAE0XQ0Q
            """
            await event.reply(help_text)
        
        @self.bot_client.on(events.CallbackQuery)
        async def callback_handler(event):
            user_id = event.sender_id
            data = event.data.decode('utf-8')
            
            if data == "start_parsing":
                stats = await self.get_user_stats(user_id)
                if stats['remaining'] <= 0:
                    minutes_left = int(stats['remaining_time'] // 60)
                    await event.answer(f"❌ Лимит исчерпан! Ждите {minutes_left} мин", alert=True)
                    return
                
                parse_text = """
🔍 Отправьте ссылку на публичный чат:

Примеры:
@telegram
https://t.me/telegram
https://t.me/joinchat/AAAAAE0XQ0Q
                """
                await event.edit(parse_text)
            
            elif data == "show_stats":
                await stats_handler(event)
        
        @self.bot_client.on(events.NewMessage)
        async def message_handler(event):
            user_id = event.sender_id
            text = event.text.strip()
            
            if text.startswith('/'):
                return
            
            # Проверяем, похоже ли сообщение на ссылку чата
            if self.is_chat_link(text):
                await self.process_chat_parsing(event, text, user_id)
            else:
                await event.reply("❌ Это не похоже на ссылку чата. Используйте /help для справки")
    
    def is_chat_link(self, text):
        """Проверяет, является ли текст ссылкой на чат"""
        patterns = [
            r'^@[a-zA-Z0-9_]{5,32}$',
            r'^https://t\.me/[a-zA-Z0-9_]{5,32}$',
            r'^https://t\.me/joinchat/[a-zA-Z0-9_-]+$'
        ]
        
        for pattern in patterns:
            if re.match(pattern, text):
                return True
        return False
    
    async def process_chat_parsing(self, event, chat_link, user_id):
        """Обрабатывает парсинг чата"""
        try:
            stats = await self.get_user_stats(user_id)
            if stats['remaining'] <= 0:
                minutes_left = int(stats['remaining_time'] // 60)
                await event.reply(f"❌ Лимит исчерпан! Подождите {minutes_left} минут")
                return
            
            # Извлекаем username или invite ссылку
            if chat_link.startswith('@'):
                chat_username = chat_link[1:]
            elif 'joinchat/' in chat_link:
                chat_username = chat_link
            else:
                chat_username = chat_link.split('/')[-1]
            
            await event.reply(f"🔍 Начинаю парсинг чата: {chat_username}")
            
            # Анимация процесса
            message = await event.reply("🔄 Подключаюсь к чату...")
            
            try:
                # Получаем информацию о чате
                if 'joinchat/' in chat_username:
                    chat = await self.bot_client.get_entity(chat_username)
                else:
                    chat = await self.bot_client.get_entity(chat_username)
                
                await message.edit("✅ Чат найден! Собираю участников...")
                
                # Собираем участников
                participants = []
                async for user in self.bot_client.iter_participants(chat, limit=100):
                    if not user.bot and user.username:  # Только пользователи с username
                        participants.append({
                            'id': user.id,
                            'username': user.username,
                            'first_name': user.first_name or '',
                            'last_name': user.last_name or ''
                        })
                
                if len(participants) < 50:
                    await message.edit(f"❌ В чате слишком мало пользователей с username ({len(participants)}). Нужно минимум 50.")
                    return
                
                await message.edit(f"✅ Собрано {len(participants)} пользователей! Сохраняю в файл...")
                
                # Сохраняем в файл
                filename = f"users_{chat_username.replace('/', '_')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"Парсинг чата: {chat_username}\n")
                    f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Всего пользователей: {len(participants)}\n\n")
                    
                    for i, user in enumerate(participants, 1):
                        f.write(f"{i}. @{user['username']} | ID: {user['id']} | {user['first_name']} {user['last_name']}\n")
                
                # Отправляем файл пользователю
                await message.edit("📁 Файл готов! Отправляю...")
                
                result_text = f"""
✅ Парсинг завершен!

📊 Результаты:
• Чат: {chat_username}
• Пользователей собрано: {len(participants)}
• Файл: {filename}

💾 Файл содержит:
- Username пользователей
- User ID
- Имена и фамилии
                """
                
                await self.bot_client.send_file(
                    event.chat_id,
                    filename,
                    caption=result_text
                )
                
                # Увеличиваем счетчик запросов
                await self.increment_request_count(user_id)
                
                # Обновляем статистику
                stats = await self.get_user_stats(user_id)
                await event.reply(f"🔄 Осталось запросов: {stats['remaining']}/5")
                
            except Exception as e:
                await message.edit(f"❌ Ошибка при парсинге: {str(e)}")
                logger.error(f"Error parsing chat: {e}")
                
        except Exception as e:
            await event.reply("❌ Ошибка при обработке запроса")
            logger.error(f"Error in process_chat_parsing: {e}")
    
    async def run(self):
        """Запуск бота"""
        await self.initialize()
        logger.info("Парсер бот запущен и готов к работе")
        await self.bot_client.run_until_disconnected()

# Запуск бота
if __name__ == '__main__':
    import time
    from datetime import datetime
    
    bot = TelegramParserBot()
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        if hasattr(bot, 'conn'):
            bot.conn.close()
