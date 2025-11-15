import asyncio
import logging
import time
import random
import sqlite3
from datetime import datetime
from telethon import TelegramClient, events, Button

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComplaintBot:
    def __init__(self):
        self.API_ID = '29385016'
        self.API_HASH = '3c57df8805ab5de5a23a032ed39b9af9'
        self.BOT_TOKEN = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'
        
        self.bot_client = None
        self.setup_database()
    
    def setup_database(self):
        """Настройка базы данных для хранения запросов"""
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
        logger.info("Бот инициализирован")
    
    def setup_handlers(self):
        """Настройка обработчиков событий"""
        
        @self.bot_client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            user_id = event.sender_id
            stats = await self.get_user_stats(user_id)
            
            welcome_text = f"""
User Checker & Complaint Bot

У вас {stats['remaining']}/5 запросов

Отправьте @username или user_id для проверки
            """
            
            buttons = [
                [Button.inline("Отправить жалобу", b"show_complaint_form")],
                [Button.inline("Моя статистика", b"show_stats")]
            ]
            
            await event.reply(welcome_text, buttons=buttons)
        
        @self.bot_client.on(events.NewMessage(pattern='/stats'))
        async def stats_handler(event):
            user_id = event.sender_id
            stats = await self.get_user_stats(user_id)
            
            minutes_left = int(stats['remaining_time'] // 60)
            seconds_left = int(stats['remaining_time'] % 60)
            
            stats_text = f"""
Статистика:

Использовано: {stats['used']}/5
Осталось: {stats['remaining']}
Сброс через: {minutes_left}мин {seconds_left}сек
            """
            
            await event.reply(stats_text)
        
        @self.bot_client.on(events.CallbackQuery)
        async def callback_handler(event):
            user_id = event.sender_id
            data = event.data.decode('utf-8')
            
            if data == "show_complaint_form":
                stats = await self.get_user_stats(user_id)
                if stats['remaining'] <= 0:
                    minutes_left = int(stats['remaining_time'] // 60)
                    await event.answer(f"Лимит исчерпан! Ждите {minutes_left} мин", alert=True)
                    return
                
                complaint_text = """
Введите username или user_id пользователя:

Примеры:
@username 
123456789
username
                """
                await event.edit(complaint_text)
                
            elif data == "show_stats":
                await stats_handler(event)
            
            elif data.startswith("complaint_"):
                target_username = data.replace("complaint_", "")
                await self.send_complaint_animation(event, user_id, target_username)
        
        @self.bot_client.on(events.NewMessage)
        async def message_handler(event):
            user_id = event.sender_id
            text = event.text.strip()
            
            if text.startswith('/'):
                return
            
            stats = await self.get_user_stats(user_id)
            if stats['remaining'] <= 0:
                minutes_left = int(stats['remaining_time'] // 60)
                await event.reply(f"Лимит исчерпан! Подождите {minutes_left} минут")
                return
            
            if self.is_valid_input(text):
                await self.process_user_check(event, text, user_id)
            else:
                await event.reply("Неверный формат. Введите @username или user_id")
    
    def is_valid_input(self, text):
        """Проверяет валидность ввода"""
        if text.startswith('@'):
            return len(text) <= 33 and text[1:].replace('_', '').isalnum()
        elif text.isdigit():
            return len(text) >= 5 and len(text) <= 15
        else:
            return len(text) <= 32 and text.replace('_', '').isalnum()
    
    async def process_user_check(self, event, input_text, user_id):
        """Обрабатывает проверку пользователя"""
        try:
            clean_input = input_text.replace('@', '')
            await event.reply(f"Проверяю {clean_input}...")
            
            try:
                if clean_input.isdigit():
                    user = await self.bot_client.get_entity(int(clean_input))
                else:
                    user = await self.bot_client.get_entity(clean_input)
                
                response = f"""
Пользователь найден!

Имя: {user.first_name or 'Не указано'}
Фамилия: {user.last_name or 'Не указана'}
Username: @{user.username or 'Не указан'}
ID: {user.id}
Тип: {'Бот' if user.bot else 'Пользователь'}
                """
                
                buttons = [
                    [Button.inline("Отправить жалобу", f"complaint_{clean_input}".encode())]
                ]
                
                await event.reply(response, buttons=buttons)
                
            except Exception:
                await event.reply(f"Пользователь {clean_input} не существует")
                
        except Exception as e:
            await event.reply("Ошибка при проверке пользователя")
            logger.error(f"Error in process_user_check: {e}")
    
    async def send_complaint_animation(self, event, user_id, target_username):
        """Анимация отправки жалоб"""
        try:
            message = await event.edit("Начинаем отправку жалоб...")
            
            # Более медленная анимация прогресса
            progress_data = [
                ("▱▱▱▱▱", "0%"),
                ("▰▱▱▱▱", "20%"),
                ("▰▰▱▱▱", "40%"),
                ("▰▰▰▱▱", "60%"),
                ("▰▰▰▰▱", "80%"),
                ("▰▰▰▰▰", "100%")
            ]
            
            for progress_bar, percentage in progress_data:
                await asyncio.sleep(3)  # Увеличил задержку до 3 секунд
                await message.edit(f"Отправка жалоб...\n{progress_bar} {percentage}")
            
            # Генерируем результаты
            total_complaints = random.randint(250, 300)
            successful = total_complaints
            failed = 0
            
            if random.random() < 0.12:
                failed = random.randint(1, total_complaints // 8)
                successful = total_complaints - failed
            
            # Финальный результат без лишней информации
            result_text = f"""
Жалобы отправлены!

༼ つ ◕_◕ ༽つ Отправлено: {successful}
¯\_(ツ)_/¯ Не отправлено: {failed}

Цель: @{target_username}
            """
            
            await message.edit(result_text)
            
            # Увеличиваем счетчик ТОЛЬКО после отправки жалоб
            await self.increment_request_count(user_id)
            
        except Exception as e:
            logger.error(f"Error in complaint animation: {e}")
            await event.answer("Ошибка при отправке жалоб", alert=True)
    
    async def run(self):
        """Запуск бота"""
        await self.initialize()
        logger.info("Бот запущен и готов к работе")
        await self.bot_client.run_until_disconnected()

# Запуск бота
if __name__ == '__main__':
    bot = ComplaintBot()
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        if hasattr(bot, 'conn'):
            bot.conn.close()
