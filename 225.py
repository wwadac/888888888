import asyncio
import logging
import time
import random
import sqlite3
from datetime import datetime, timedelta
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
                last_reset_time REAL,
                last_request_time REAL
            )
        ''')
        self.conn.commit()
    
    async def check_user_limit(self, user_id):
        """Проверяет лимит запросов для пользователя"""
        now = time.time()
        
        # Получаем данные пользователя
        self.cursor.execute(
            'SELECT request_count, last_reset_time FROM user_requests WHERE user_id = ?',
            (user_id,)
        )
        result = self.cursor.fetchone()
        
        if not result:
            # Новый пользователь
            self.cursor.execute(
                'INSERT INTO user_requests (user_id, request_count, last_reset_time, last_request_time) VALUES (?, ?, ?, ?)',
                (user_id, 1, now, now)
            )
            self.conn.commit()
            return True, 4  # Осталось запросов
        
        request_count, last_reset_time = result
        
        # Проверяем, прошло ли 40 минут
        if now - last_reset_time >= 2400:  # 40 минут в секундах
            # Сбрасываем счетчик
            self.cursor.execute(
                'UPDATE user_requests SET request_count = 1, last_reset_time = ?, last_request_time = ? WHERE user_id = ?',
                (now, now, user_id)
            )
            self.conn.commit()
            return True, 4
        else:
            if request_count >= 5:
                return False, 0
            else:
                # Увеличиваем счетчик
                self.cursor.execute(
                    'UPDATE user_requests SET request_count = request_count + 1, last_request_time = ? WHERE user_id = ?',
                    (now, user_id)
                )
                self.conn.commit()
                return True, 4 - request_count
    
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
            remaining = max(0, 2400 - elapsed)  # 40 минут - прошедшее время
            return remaining
        return 0
    
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
            allowed, remaining = await self.check_user_limit(user_id)
            
            welcome_text = f"""
🤖 **User Checker & Complaint Bot**

⚠️ **Внимание!** У вас только **5 запросов** в течение **40 минут**

📊 **Статус:** {f"✅ Доступно запросов: {remaining}" if allowed else "❌ Лимит исчерпан"}

**Доступные команды:**
• Просто отправьте @username или user_id
• /check - Проверить пользователя
• /stats - Ваша статистика
• /help - Помощь

🎯 **Отправьте username для проверки:**
            """
            
            buttons = [
                [Button.inline("📝 Отправить жалобу", b"show_complaint_form")],
                [Button.inline("📊 Моя статистика", b"show_stats")]
            ]
            
            await event.reply(welcome_text, buttons=buttons)
        
        @self.bot_client.on(events.NewMessage(pattern='/stats'))
        async def stats_handler(event):
            user_id = event.sender_id
            remaining_time = await self.get_remaining_time(user_id)
            
            self.cursor.execute(
                'SELECT request_count FROM user_requests WHERE user_id = ?',
                (user_id,)
            )
            result = self.cursor.fetchone()
            
            if result:
                used_requests = result[0]
                remaining_requests = max(0, 5 - used_requests)
                minutes_left = int(remaining_time // 60)
                seconds_left = int(remaining_time % 60)
                
                stats_text = f"""
📊 **Ваша статистика:**

✅ Использовано запросов: {used_requests}/5
⏰ Оставшееся время: {minutes_left}мин {seconds_left}сек
🔄 Сброс через: {minutes_left} минут

💡 Лимит обновляется каждые 40 минут
                """
            else:
                stats_text = "📊 У вас еще не было запросов"
            
            await event.reply(stats_text)
        
        @self.bot_client.on(events.CallbackQuery)
        async def callback_handler(event):
            user_id = event.sender_id
            data = event.data.decode('utf-8')
            
            if data == "show_complaint_form":
                # Проверяем лимит
                allowed, remaining = await self.check_user_limit(user_id)
                if not allowed:
                    remaining_time = await self.get_remaining_time(user_id)
                    minutes_left = int(remaining_time // 60)
                    await event.answer(f"❌ Лимит исчерпан! Ждите {minutes_left} мин", alert=True)
                    return
                
                complaint_text = """
📝 **Форма отправки жалобы**

Введите username или user_id пользователя для проверки и отправки жалобы:

**Примеры:**
• `@username` 
• `123456789` (user_id)
• `username` (без @)

⬇️ **Отправьте username/user_id ниже:**
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
            
            # Игнорируем команды
            if text.startswith('/'):
                return
            
            # Проверяем лимит
            allowed, remaining = await self.check_user_limit(user_id)
            if not allowed:
                remaining_time = await self.get_remaining_time(user_id)
                minutes_left = int(remaining_time // 60)
                await event.reply(f"❌ **Лимит исчерпан!**\nПодождите {minutes_left} минут до сброса")
                return
            
            # Проверяем, похоже ли на username или ID
            if self.is_valid_input(text):
                await self.process_user_check(event, text, user_id)
            else:
                await event.reply("❌ Неверный формат. Введите @username или user_id")
    
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
            await event.reply(f"🔍 Проверяю `{clean_input}`...")
            
            # Пытаемся получить информацию о пользователе
            try:
                if clean_input.isdigit():
                    user = await self.bot_client.get_entity(int(clean_input))
                else:
                    user = await self.bot_client.get_entity(clean_input)
                
                # Пользователь найден
                user_type = "🤖 Бот" if user.bot else "👤 Пользователь"
                response = f"""
✅ **Пользователь найден!**

**👤 Имя:** {user.first_name or 'Не указано'}
**📝 Фамилия:** {user.last_name or 'Не указана'}
**🎯 Username:** @{user.username or 'Не указан'}
**🆔 ID:** `{user.id}`
**📊 Тип:** {user_type}
                """
                
                # Кнопка для отправки жалобы
                buttons = [
                    [Button.inline("🚨 Отправить жалобу", f"complaint_{clean_input}".encode())]
                ]
                
                await event.reply(response, buttons=buttons)
                
            except Exception as e:
                await event.reply(f"❌ Пользователь `{clean_input}` не существует или аккаунт приватный")
                logger.error(f"Error checking {clean_input}: {e}")
                
        except Exception as e:
            await event.reply("❌ Произошла ошибка при проверке пользователя")
            logger.error(f"Error in process_user_check: {e}")
    
    async def send_complaint_animation(self, event, user_id, target_username):
        """Анимация отправки жалоб"""
        try:
            # Этапы анимации
            stages = [
                "🔄 Подготавливаем базу данных жалоб...",
                "📡 Устанавливаем соединение с серверами Telegram...",
                "🔍 Анализируем профиль пользователя...",
                "📝 Формируем пакеты жалоб...",
                "🚀 Начинаем отправку жалоб..."
            ]
            
            message = await event.edit("⏳ **Начинаем процесс отправки жалоб...**")
            
            # Проходим этапы подготовки
            for stage in stages:
                await asyncio.sleep(2)
                await message.edit(f"⏳ {stage}")
            
            # Генерируем результаты
            total_complaints = random.randint(250, 300)
            successful = total_complaints
            failed = 0
            
            # 12% шанс на ошибки
            if random.random() < 0.12:
                failed = random.randint(1, total_complaints // 8)
                successful = total_complaints - failed
            
            # Анимация прогресса
            progress_stages = [
                ("▰▱▱▱▱▱▱▱▱", "10%"),
                ("▰▰▰▱▱▱▱▱▱", "30%"),
                ("▰▰▰▰▰▰▱▱▱", "60%"),
                ("▰▰▰▰▰▰▰▰▰▱", "90%"),
                ("▰▰▰▰▰▰▰▰▰▰", "100%")
            ]
            
            for progress_bar, percentage in progress_stages:
                await asyncio.sleep(1.5)
                await message.edit(f"📤 **Отправка жалоб...**\n{progress_bar} {percentage}")
            
            # Финальный результат
            result_text = f"""
✅ **Жалобы успешно отправлены!**

📊 **Результаты отправки:**
• 📨 Отправлено: {successful}
• ❌ Не отправлено: {failed}
• 📊 Эффективность: {((successful/total_complaints)*100):.1f}%

🎯 **Цель:** @{target_username}
⏰ **Время:** {datetime.now().strftime('%H:%M:%S')}

⚠️ Жалобы будут обработаны в течение 24 часов
            """
            
            await message.edit(result_text)
            
            # Обновляем счетчик запросов
            self.cursor.execute(
                'UPDATE user_requests SET request_count = request_count + 1 WHERE user_id = ?',
                (user_id,)
            )
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Error in complaint animation: {e}")
            await event.answer("❌ Ошибка при отправке жалоб", alert=True)
    
    async def run(self):
        """Запуск бота"""
        await self.initialize()
        logger.info("Бот запущен и готов к работе")
        
        me = await self.bot_client.get_me()
        logger.info(f"Бот @{me.username} успешно запущен!")
        
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
