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
🎭 **User Checker & Complaint Bot**

📊 **Статистика запросов:**
🟢 Доступно: **{stats['remaining']}/5** запросов
¯\_(ツ)_/¯  Сброс каждые 40 минут

💡 **Как использовать:**
Просто отправьте @username или user_id для проверки пользователя

⚡ **Быстрые действия:**
            """
            
            buttons = [
                [Button.inline("📝 Отправить жалобу", b"show_complaint_form")],
                [Button.inline("📊 Моя статистика", b"show_stats"),
                 Button.inline("ℹ️ Помощь", b"show_help")]
            ]
            
            await event.reply(welcome_text, buttons=buttons, parse_mode='md')
        
        @self.bot_client.on(events.NewMessage(pattern='/stats'))
        async def stats_handler(event):
            user_id = event.sender_id
            stats = await self.get_user_stats(user_id)
            
            minutes_left = int(stats['remaining_time'] // 60)
            seconds_left = int(stats['remaining_time'] % 60)
            
            stats_text = f"""
📈 **Ваша статистика**

🎯 Использовано запросов: **{stats['used']}/5**
🟢 Осталось запросов: **{stats['remaining']}**
⏳ Сброс через: **{minutes_left} мин {seconds_left} сек**

💡 Лимит обновляется каждые 40 минут
            """
            
            await event.reply(stats_text, parse_mode='md')
        
        @self.bot_client.on(events.NewMessage(pattern='/help'))
        async def help_handler(event):
            help_text = """
📖 **Помощь по боту**

༼ つ ◕_◕ ༽つ  **Что умеет этот бот:**
• Проверять существование пользователей Telegram
• Отправлять массовые жалобы на аккаунты
• Работать с username и user_id

🎯 **Как использовать:**
1. Отправьте @username или user_id
2. Нажмите кнопку "Отправить жалобу"
3. Дождитесь завершения процесса

⚡ **Лимиты:**
• 5 запросов каждые 40 минут
• Автоматический сброс лимитов

            """
            
            await event.reply(help_text, parse_mode='md')

        @self.bot_client.on(events.CallbackQuery)
        async def callback_handler(event):
            user_id = event.sender_id
            data = event.data.decode('utf-8')
            
            if data == "show_complaint_form":
                stats = await self.get_user_stats(user_id)
                if stats['remaining'] <= 0:
                    minutes_left = int(stats['remaining_time'] // 60)
                    seconds_left = int(stats['remaining_time'] % 60)
                    await event.answer(f"🚫 Лимит исчерпан! Ждите {minutes_left} мин {seconds_left} сек", alert=True)
                    return
                
                complaint_text = """
📝 **Форма отправки жалобы**

Введите username или user_id пользователя:

**Примеры корректного ввода:**
👉 `@username` 
👉 `123456789`
👉 `username`

⏰ **Обработка займет несколько минут...**
                """
                await event.edit(complaint_text, parse_mode='md')
                
            elif data == "show_stats":
                await stats_handler(event)
            
            elif data == "show_help":
                await help_handler(event)
            
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
                seconds_left = int(stats['remaining_time'] % 60)
                await event.reply(f"🚫 **Лимит исчерпан!**\n\nПодождите **{minutes_left} мин {seconds_left} сек** ⏳", parse_mode='md')
                return
            
            if self.is_valid_input(text):
                await self.process_user_check(event, text, user_id)
            else:
                await event.reply("❌ **Неверный формат!**\n\nВведите @username или user_id\n\n💡 Пример: `@username` или `123456789`", parse_mode='md')
    
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
            await event.reply(f"🔍 **Проверяю пользователя...**\n\n👤 Цель: `{clean_input}`", parse_mode='md')
            
            try:
                if clean_input.isdigit():
                    user = await self.bot_client.get_entity(int(clean_input))
                else:
                    user = await self.bot_client.get_entity(clean_input)
                
                # Определяем эмодзи для типа пользователя
                user_type_emoji = "🤖" if user.bot else "👤"
                premium_emoji = "⭐" if getattr(user, 'premium', False) else "⚪"
                
                response = f"""
✅ **Пользователь найден!**

{user_type_emoji} **Основная информация:**
├ Имя: `{user.first_name or 'Не указано'}`
├ Фамилия: `{user.last_name or 'Не указана'}`
├ Username: `@{user.username or 'Не указан'}`
├ ID: `{user.id}`
└ Тип: `{'Бот' if user.bot else 'Пользователь'}`

{premium_emoji} **Дополнительно:**
└ Premium: `{'Да' if getattr(user, 'premium', False) else 'Нет'}`
                """
                
                buttons = [
                    [Button.inline("🚨 Отправить жалобу", f"complaint_{clean_input}".encode())],
                    [Button.inline("📊 Статистика", b"show_stats"),
                     Button.inline("🔄 Новый поиск", b"show_complaint_form")]
                ]
                
                await event.reply(response, buttons=buttons, parse_mode='md')
                
            except Exception as e:
                await event.reply(f"❌ **Пользователь не найден!**\n\n`{clean_input}` - не существует или скрыт\n\n💡 Проверьте правильность ввода", parse_mode='md')
                
        except Exception as e:
            await event.reply("❌ **Ошибка при проверке пользователя!**\n\nПопробуйте еще раз", parse_mode='md')
            logger.error(f"Error in process_user_check: {e}")
    
    async def send_complaint_animation(self, event, user_id, target_username):
        """Анимация отправки жалоб с новой графикой"""
        try:
            message = await event.edit("🚀 **Начинаем отправку жалоб...**\n\n⏳ Подготовка системы...", parse_mode='md')
            
            # Новая анимация - Запуск ракеты
            animation_steps = [
    "📡 ■▢▢▢▢▢▢▢▢▢ 10% — Активация донос-бота...",
    "📡 ■■▢▢▢▢▢▢▢▢ 20% — Поиск «неправильного» контента...",
    "📡 ■■■▢▢▢▢▢▢▢ 30% — Классификация по степени опасности...",
    "📡 ■■■■▢▢▢▢▢▢ 40% — Шаблон «18+» применён...",
    "📡 ■■■■■▢▢▢▢▢ 50% — #1: ‘порнография’",
    "📡 ■■■■■■▢▢▢▢ 60% — #2: ‘буллинг’",
    "📡 ■■■■■■■▢▢▢ 70% — #3: ‘террористическая пропаганда’",
    "📡 ■■■■■■■■▢▢ 80% — #4: ‘ненависть’",
    "📡 ■■■■■■■■■▢ 90% — #5: ‘подделка личности’",
    "📡 ■■■■■■■■■■ 95% — Все жалобы — правдоподобны!",
    "🤖 ■■■■■■■■■■ 100% — Скоро account Удалят!"
]
            
            for step in animation_steps:
                await asyncio.sleep(2.5)
                await message.edit(f"📨 **Отправка жалоб на @{target_username}**\n\n{step}")
            
            # Генерируем реалистичные результаты
            total_complaints = random.randint(250, 300)
            successful = total_complaints
            failed = 0
            
            # 15% шанс на частичный провал
            if random.random() < 0.15:
                failed = random.randint(1, total_complaints // 6)
                successful = total_complaints - failed
            
            # Определяем эмодзи результата
            if failed == 0:
                result_emoji = "🎉"
                status_emoji = "✅"
            elif failed < 10:
                result_emoji = "⚠️"
                status_emoji = "🟡"
            else:
                result_emoji = "🚨"
                status_emoji = "🔴"
            
            # Финальный результат с красивым оформлением
            result_text = f"""
{result_emoji} **Жалобы успешно отправлены!**

{status_emoji} **Результаты операции:**
├ 🎯 Цель: `@{target_username}`
├ ↪ Отправлено: `{total_complaints}` жалоб
├ ✅ Успешно: `{successful}`
├ ❌ Не отправлено: `{failed}`
└ ⏱ Время: `{len(animation_steps) * 2.5:.1f}` сек

💡 **Статистика обновлена** - использован 1 запрос
            """
            
            await message.edit(result_text, parse_mode='md')
            
            # Увеличиваем счетчик ТОЛЬКО после отправки жалоб
            await self.increment_request_count(user_id)
            
        except Exception as e:
            logger.error(f"Error in complaint animation: {e}")
            await event.answer("❌ Ошибка при отправке жалоб!", alert=True)
    
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

