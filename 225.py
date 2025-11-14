import telebot
import pandas as pd
import re
import os
import time
from io import BytesIO
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore

# === НАСТРОЙКИ ===
TOKEN = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'
ADMIN_USER_ID = 8000395560  # Замените на ваш ID (узнать через @userinfobot)

bot = telebot.TeleBot(TOKEN)
scheduler = BackgroundScheduler(jobstores={'default': MemoryJobStore()})
scheduler.start()

# Глобальные настройки
config = {
    'target_chat_id': None,      # Куда слать @username
    'interval_sec': 300,         # По умолчанию — каждые 5 минут
    'usernames': [],             # Список @username из файла
    'current_index': 0,          # Текущая позиция в списке
    'is_active': False           # Работает ли рассылка
}

job_id = 'send_users_job'

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def send_next_user():
    if not config['is_active'] or not config['usernames']:
        return
    if config['current_index'] >= len(config['usernames']):
        bot.send_message(ADMIN_USER_ID, "✅ Рассылка завершена!")
        config['is_active'] = False
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
        return

    username = config['usernames'][config['current_index']]
    try:
        bot.send_message(config['target_chat_id'], username)
        config['current_index'] += 1
    except Exception as e:
        bot.send_message(ADMIN_USER_ID, f"❌ Ошибка отправки в чат: {e}")
        config['is_active'] = False
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

# === АДМИН-КОМАНДЫ ===

@bot.message_handler(commands=['start', 'help'])
def cmd_help(message):
    if message.from_user.id != ADMIN_USER_ID:
        bot.reply_to(message, "❌ Доступ запрещён.")
        return
    help_text = """
🤖 **Админ-панель рассылки**:

`/setchat <ID>` — установить ID чата/группы
`/interval <сек>` — интервал между отправками (например, 300 = 5 мин)
`/status` — показать текущие настройки
`/startsend` — запустить рассылку
`/stopsend` — остановить рассылку

📎 Просто отправьте Excel-файл (.xlsx), и бот извлечёт @username.
"""
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['setchat'])
def cmd_set_chat(message):
    if message.from_user.id != ADMIN_USER_ID:
        return
    try:
        chat_id = int(message.text.split()[1])
        config['target_chat_id'] = chat_id
        bot.reply_to(message, f"✅ Целевой чат установлен: `{chat_id}`", parse_mode='Markdown')
    except (IndexError, ValueError):
        bot.reply_to(message, "❌ Укажите корректный ID чата: `/setchat -1001234567890`", parse_mode='Markdown')

@bot.message_handler(commands=['interval'])
def cmd_set_interval(message):
    if message.from_user.id != ADMIN_USER_ID:
        return
    try:
        sec = int(message.text.split()[1])
        if sec < 10:
            bot.reply_to(message, "⚠️ Минимальный интервал — 10 секунд.")
            return
        config['interval_sec'] = sec
        bot.reply_to(message, f"✅ Интервал установлен: {sec} секунд")
    except (IndexError, ValueError):
        bot.reply_to(message, "❌ Используйте: `/interval 300`", parse_mode='Markdown')

@bot.message_handler(commands=['status'])
def cmd_status(message):
    if message.from_user.id != ADMIN_USER_ID:
        return
    status = f"""
📊 **Статус**:
- Целевой чат: `{config['target_chat_id'] or 'не задан'}`
- Всего пользователей: {len(config['usernames'])}
- Отправлено: {config['current_index']}
- Интервал: {config['interval_sec']} сек
- Состояние: {'🟢 активна' if config['is_active'] else '🔴 остановлена'}
"""
    bot.send_message(message.chat.id, status, parse_mode='Markdown')

@bot.message_handler(commands=['startsend'])
def cmd_start_send(message):
    if message.from_user.id != ADMIN_USER_ID:
        return
    if not config['target_chat_id']:
        bot.reply_to(message, "❌ Сначала установите чат: `/setchat <ID>`")
        return
    if not config['usernames']:
        bot.reply_to(message, "❌ Сначала загрузите Excel-файл с @username")
        return
    if config['current_index'] >= len(config['usernames']):
        bot.reply_to(message, "ℹ️ Все пользователи уже отправлены. Загрузите новый файл.")
        return

    config['is_active'] = True
    # Удаляем старую задачу, если есть
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    scheduler.add_job(send_next_user, 'interval', seconds=config['interval_sec'], id=job_id)
    bot.reply_to(message, f"✅ Рассылка запущена! Первый юзер отправится через {config['interval_sec']} сек.")

@bot.message_handler(commands=['stopsend'])
def cmd_stop_send(message):
    if message.from_user.id != ADMIN_USER_ID:
        return
    config['is_active'] = False
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    bot.reply_to(message, "⏹️ Рассылка остановлена.")

# === ЗАГРУЗКА ФАЙЛА ===

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if message.from_user.id != ADMIN_USER_ID:
        bot.reply_to(message, "❌ Только админ может загружать файлы.")
        return

    try:
        if not message.document.file_name.endswith('.xlsx'):
            bot.reply_to(message, "📁 Отправьте файл с расширением `.xlsx`")
            return

        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        excel_data = pd.read_excel(
            BytesIO(downloaded_file),
            header=None,
            dtype=str,
            engine='openpyxl'
        )

        first_col = excel_data.iloc[:, 0].dropna().astype(str).str.strip()
        links = first_col[first_col.str.contains(r'https?://t\.me/', na=False)]

        usernames = []
        for link in links:
            match = re.search(r'https?://t\.me/([a-zA-Z0-9_]+)', link)
            if match:
                usernames.append('@' + match.group(1))

        if not usernames:
            bot.reply_to(message, "⚠️ В файле не найдено корректных ссылок на Telegram.")
            return

        config['usernames'] = usernames
        config['current_index'] = 0
        config['is_active'] = False
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

        bot.reply_to(message, f"✅ Загружено {len(usernames)} @username. Готово к рассылке!\n\nИспользуйте `/startsend` для запуска.")

    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# === ЗАПУСК ===

if __name__ == '__main__':
    print("✅ Бот запущен...")
    try:
        bot.polling(none_stop=True, timeout=60)
    except KeyboardInterrupt:
        scheduler.shutdown()
