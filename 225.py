import asyncio
import logging
import sqlite3
import time
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramParserBot:
    def __init__(self):
        # Бот для управления
        self.BOT_TOKEN = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'
        
        # User-аккаунт для парсинга (нужно получить session string)
        self.API_ID = '29385016'
        self.API_HASH = '3c57df8805ab5de5a23a032ed39b9af9'
        self.USER_SESSION = None  # Нужно установить через /auth
        
        self.bot_client = None
        self.user_client = None
        self.setup_database()
    
    def setup_database(self):
        """Настройка базы данных"""
        self.conn = sqlite3.connect('user_limits.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_requests (
                user_id INTEGER PRIMARY KEY,
                request_count INTEGER DEFAULT 0,
                last_reset_time REAL
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                user_id INTEGER PRIMARY KEY,
                session_string TEXT
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
        
        if now - last_reset_time >= 2400:  # 40 минут
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
    
    async def get_user_stats(self, user_id):
        """Получает статистику пользователя"""
        self.cursor.execute(
            'SELECT request_count, last_reset_time FROM user_requests WHERE user_id = ?',
            (user_id,)
        )
        result = self.cursor.fetchone()
        
        if result:
            request_count, last_reset_time = result
            elapsed = time.time() - last_reset_time
            remaining_time = max(0, 2400 - elapsed)
            return {
                'used': request_count,
                'remaining': max(0, 5 - request_count),
                'remaining_time': remaining_time
            }
        return {'used': 0, 'remaining': 5, 'remaining_time': 0}
    
    async def get_user_session(self, user_id):
        """Получает session string пользователя"""
        self.cursor.execute(
            'SELECT session_string FROM user_sessions WHERE user_id = ?',
            (user_id,)
        )
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    async def save_user_session(self, user_id, session_string):
        """Сохраняет session string пользователя"""
        self.cursor.execute(
            'INSERT OR REPLACE INTO user_sessions (user_id, session_string) VALUES (?, ?)',
            (user_id, session_string)
        )
        self.conn.commit()
    
    async def initialize_user_client(self, user_id):
        """Инициализирует user-клиент для парсинга"""
        try:
            session_string = await self.get_user_session(user_id)
            if not session_string:
                return None, "❌ Сначала выполните авторизацию через /auth"
            
            self.user_client = TelegramClient(
                StringSession(session_string), 
                self.API_ID, 
                self.API_HASH
            )
            
            await self.user_client.start()
            return self.user_client, "✅ User-клиент авторизован"
            
        except Exception as e:
            return None, f"❌ Ошибка авторизации: {str(e)}"
    
    async def initialize_bot(self):
        """Инициализация бота"""
        self.bot_client = TelegramClient(
            'bot_session', 
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
            user_id = event.sender_id
            stats = await self.get_user_stats(user_id)
            
            welcome_text = f"""
🤖 Telegram Parser Bot

У вас {stats['remaining']}/5 запросов на парсинг

🔐 Требуется авторизация:
1. Используйте /auth для получения инструкций
2. После авторизации используйте /parse

Бот соберет 1-50 пользователей из чата
            """
            
            buttons = [
                [Button.inline("🔐 Авторизация", b"show_auth")],
                [Button.inline("🔍 Парсинг", b"start_parsing")],
                [Button.inline("📊 Статистика", b"show_stats")]
            ]
            
            await event.reply(welcome_text, buttons=buttons)
        
        @self.bot_client.on(events.NewMessage(pattern='/auth'))
        async def auth_handler(event):
            auth_instructions = """
🔐 **Авторизация User-аккаунта**

Для парсинга чатов нужен user-аккаунт:

1. Перейдите на @genStr_robot
2. Получите session string
3. Отправьте его мне в формате:
   `1a2b3c4d...` (длинная строка)

После авторизации можно парсить чаты!
            """
            await event.reply(auth_instructions)
        
        @self.bot_client.on(events.NewMessage(pattern='/parse'))
        async def parse_handler(event):
            user_id = event.sender_id
            
            # Проверяем авторизацию
            session_string = await self.get_user_session(user_id)
            if not session_string:
                await event.reply("❌ Сначала выполните авторизацию через /auth")
                return
            
            stats = await self.get_user_stats(user_id)
            if stats['remaining'] <= 0:
                minutes_left = int(stats['remaining_time'] // 60)
                await event.reply(f"❌ Лимит исчерпан! Подождите {minutes_left} минут")
                return
            
            parse_instructions = """
🔍 **Парсинг пользователей из чата**

Отправьте ссылку на публичный чат:
- @username  
- https://t.me/username

Бот соберет участников чата (1-50 человек)
            """
            await event.reply(parse_instructions)
        
        @self.bot_client.on(events.NewMessage(pattern='/stats'))
        async def stats_handler(event):
            user_id = event.sender_id
            stats = await self.get_user_stats(user_id)
            
            minutes_left = int(stats['remaining_time'] // 60)
            seconds_left = int(stats['remaining_time'] % 60)
            
            # Проверяем авторизацию
            session_string = await self.get_user_session(user_id)
            auth_status = "✅ Авторизован" if session_string else "❌ Не авторизован"
            
            stats_text = f"""
📊 Статистика:

{auth_status}
✅ Использовано: {stats['used']}/5
🔄 Осталось: {stats['remaining']}
⏰ Сброс через: {minutes_left}мин {seconds_left}сек
            """
            await event.reply(stats_text)
        
        @self.bot_client.on(events.CallbackQuery)
        async def callback_handler(event):
            user_id = event.sender_id
            data = event.data.decode('utf-8')
            
            if data == "show_auth":
                await auth_handler(event)
            
            elif data == "start_parsing":
                session_string = await self.get_user_session(user_id)
                if not session_string:
                    await event.answer("❌ Сначала выполните авторизацию!", alert=True)
                    return
                
                stats = await self.get_user_stats(user_id)
                if stats['remaining'] <= 0:
                    minutes_left = int(stats['remaining_time'] // 60)
                    await event.answer(f"❌ Лимит исчерпан! Ждите {minutes_left} мин", alert=True)
                    return
                
                parse_text = "🔍 Отправьте ссылку на публичный чат (например: @telegram)"
                await event.edit(parse_text)
            
            elif data == "show_stats":
                await stats_handler(event)
        
        @self.bot_client.on(events.NewMessage)
        async def message_handler(event):
            user_id = event.sender_id
            text = event.text.strip()
            
            if text.startswith('/'):
                return
            
            # Проверяем session string (длинная строка)
            if len(text) > 100 and all(c.isalnum() or c in '+-=' for c in text):
                await self.process_session_string(event, text, user_id)
                return
            
            # Проверяем ссылку на чат
            if self.is_chat_link(text):
                await self.process_chat_parsing(event, text, user_id)
            else:
                await event.reply("❌ Не распознано. Отправьте ссылку на чат или session string")
    
    def is_chat_link(self, text):
        """Проверяет, является ли текст ссылкой на чат"""
        return text.startswith('@') or text.startswith('https://t.me/')
    
    async def process_session_string(self, event, session_string, user_id):
        """Обрабатывает сохранение session string"""
        try:
            await self.save_user_session(user_id, session_string)
            
            # Проверяем валидность сессии
            user_client, message = await self.initialize_user_client(user_id)
            if user_client:
                me = await user_client.get_me()
                await event.reply(f"✅ Авторизация успешна!\nАккаунт: {me.first_name}\nТеперь можно использовать /parse")
            else:
                await event.reply(message)
                
        except Exception as e:
            await event.reply(f"❌ Ошибка при сохранении session: {str(e)}")
    
    async def process_chat_parsing(self, event, chat_link, user_id):
        """Обрабатывает парсинг чата"""
        try:
            # Проверяем авторизацию
            user_client, auth_message = await self.initialize_user_client(user_id)
            if not user_client:
                await event.reply(auth_message)
                return
            
            # Проверяем лимиты
            stats = await self.get_user_stats(user_id)
            if stats['remaining'] <= 0:
                minutes_left = int(stats['remaining_time'] // 60)
                await event.reply(f"❌ Лимит исчерпан! Подождите {minutes_left} минут")
                return
            
            # Извлекаем username
            if chat_link.startswith('@'):
                chat_username = chat_link[1:]
            else:
                chat_username = chat_link.split('/')[-1]
            
            await event.reply(f"🔍 Начинаю парсинг чата: {chat_username}")
            message = await event.reply("🔄 Подключаюсь к чату...")
            
            try:
                # Получаем информацию о чате
                chat = await user_client.get_entity(chat_username)
                await message.edit("✅ Чат найден! Собираю участников...")
                
                # Собираем участников (до 50)
                participants = []
                async for user in user_client.iter_participants(chat, limit=50):
                    participants.append({
                        'id': user.id,
                        'username': user.username or 'Нет username',
                        'first_name': user.first_name or '',
                        'last_name': user.last_name or '',
                        'is_bot': user.bot
                    })
                
                if not participants:
                    await message.edit("❌ Не удалось собрать участников")
                    return
                
                await message.edit(f"✅ Собрано {len(participants)} пользователей! Сохраняю...")
                
                # Сохраняем в файл
                filename = f"users_{chat_username}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"Парсинг чата: {chat_username}\n")
                    f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Участников собрано: {len(participants)}\n")
                    f.write("=" * 50 + "\n\n")
                    
                    for i, user in enumerate(participants, 1):
                        user_type = "🤖 Бот" if user['is_bot'] else "👤 Пользователь"
                        f.write(f"{i}. {user_type}\n")
                        f.write(f"   ID: {user['id']}\n")
                        f.write(f"   Username: @{user['username']}\n")
                        f.write(f"   Имя: {user['first_name']} {user['last_name']}\n")
                        if user['username'] != 'Нет username':
                            f.write(f"   Ссылка: https://t.me/{user['username']}\n")
                        f.write("-" * 30 + "\n")
                
                # Отправляем файл
                await message.edit("📁 Файл готов! Отправляю...")
                
                result_text = f"""
✅ Парсинг завершен!

📊 Результаты:
• Чат: {chat_username}
• Участников собрано: {len(participants)}
• Файл: {filename}
                """
                
                await self.bot_client.send_file(
                    event.chat_id,
                    filename,
                    caption=result_text
                )
                
                # Обновляем статистику
                await self.increment_request_count(user_id)
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
        await self.initialize_bot()
        logger.info("Бот запущен и готов к работе")
        await self.bot_client.run_until_disconnected()

# Запуск бота
if __name__ == '__main__':
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
