import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
import os
from openai import OpenAI
import sqlite3
import json
import pdfplumber 
import docx  
from io import BytesIO
import time

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename="bot.log",
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL= os.getenv("BASE_URL")

if not TELEGRAM_BOT_TOKEN or not DEEPSEEK_API_KEY:
    raise ValueError("Не установлены обязательные переменные окружения: TELEGRAM_BOT_TOKEN или DEEPSEEK_API_KEY")

# Инициализация клиента OpenAI
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=BASE_URL)

# Подключение к базе данных SQLite
conn = sqlite3.connect('bot_context.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы для хранения контекста
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_context (
    user_id INTEGER PRIMARY KEY,
    context TEXT
)
''')

# Создание таблицы для хранения данных из файлов
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_files (
    user_id INTEGER,
    file_name TEXT,
    file_content TEXT,
    PRIMARY KEY (user_id, file_name)
)
''')
conn.commit()

# Функция для получения контекста пользователя
def get_user_context(user_id):
    cursor.execute('SELECT context FROM user_context WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result and result[0].strip(): 
        try:
            return json.loads(result[0])
        except json.JSONDecodeError:
            logger.error(f"Ошибка декодирования JSON для user_id {user_id}")
            return [{"role": "system", "content": "You are a helpful assistant."}]
    return [{"role": "system", "content": "You are a helpful assistant."}]

# Функция для обновления контекста пользователя
def update_user_context(user_id, context):
    cursor.execute('''
    INSERT OR REPLACE INTO user_context (user_id, context)
    VALUES (?, ?)
    ''', (user_id, json.dumps(context))) 
    conn.commit()

# Функция для сохранения данных из файла в базу данных
def save_file_content(user_id, file_name, file_content):
    cursor.execute('''
    INSERT OR REPLACE INTO user_files (user_id, file_name, file_content)
    VALUES (?, ?, ?)
    ''', (user_id, file_name, file_content))
    conn.commit()

# Функция для получения данных из файлов пользователя
def get_file_content(user_id):
    cursor.execute('SELECT file_content FROM user_files WHERE user_id = ?', (user_id,))
    results = cursor.fetchall()
    return [result[0] for result in results] 

# Функция для обработки команды /start
async def start(update: Update, context):
    user_id = update.message.from_user.id
    update_user_context(user_id, [{"role": "system", "content": "You are a helpful assistant."}])
    await update.message.reply_text('Привет! Я бот, который может искать информацию. Отправь мне запрос или документ (PDF, DOCX, TXT), и я постараюсь найти ответ.')

# Функция для извлечения текста из PDF
def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    if not text.strip():
        raise ValueError("PDF файл не содержит текста или поврежден")
    return text

# Функция для извлечения текста из DOCX
def extract_text_from_docx(file):
    doc = docx.Document(file)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    if not text.strip():
        raise ValueError("DOCX файл не содержит текста или поврежден")
    return text

# Функция для извлечения текста из TXT
def extract_text_from_txt(file):
    text = file.read().decode('utf-8')
    if not text.strip():
        raise ValueError("TXT файл пуст или поврежден")
    return text

# Функция для обработки документов
async def handle_document(update: Update, context):
    user_id = update.message.from_user.id
    document = update.message.document

    # Проверка размера файла
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    if document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text('Файл слишком большой. Максимальный размер: 10 MB.')
        return

    # Скачиваем документ
    file = await context.bot.get_file(document.file_id)
    file_bytes = BytesIO()
    await file.download_to_memory(file_bytes)
    file_bytes.seek(0)

    # Определяем тип файла и извлекаем текст
    file_name = document.file_name.lower()
    try:
        if file_name.endswith('.pdf'):
            text = extract_text_from_pdf(file_bytes)
        elif file_name.endswith('.docx'):
            text = extract_text_from_docx(file_bytes)
        elif file_name.endswith('.txt'):
            text = extract_text_from_txt(file_bytes)
        else:
            await update.message.reply_text('Формат файла не поддерживается. Пожалуйста, отправьте PDF, DOCX или TXT.')
            return

        # Сохраняем текст из файла в базу данных
        save_file_content(user_id, file_name, text)
        await update.message.reply_text(f'Файл "{file_name}" успешно загружен и сохранен.')

    except ValueError as e:
        await update.message.reply_text(f'Ошибка при обработке файла: {e}')
    except Exception as e:
        logger.error(f"Произошла ошибка при обработке файла: {e}")
        await update.message.reply_text('Произошла ошибка при обработке вашего файла. Пожалуйста, попробуйте еще раз.')

# Функция для обработки текстовых сообщений
async def handle_message(update: Update, context):
    user_id = update.message.from_user.id
    user_message = update.message.text

    # Получаем текущий контекст пользователя
    user_context = get_user_context(user_id)

    # Ограничиваем размер контекста
    MAX_CONTEXT_SIZE = 32 * 1024  # 32 KB
    def truncate_context(context):
        serialized_context = json.dumps(context)
        if len(serialized_context) > MAX_CONTEXT_SIZE:
            logger.warning("Контекст слишком большой. Обрезка...")
            context = context[-10:]  
        return context

    user_context = truncate_context(user_context)

    # Получаем данные из файлов пользователя
    file_contents = get_file_content(user_id)
    if file_contents:
        user_context.append({"role": "user", "content": f"Данные из файлов: {' '.join(file_contents)}"})

    # Добавляем сообщение пользователя в контекст
    user_context.append({"role": "user", "content": user_message})

    max_retries = 5  # Максимальное количество повторных попыток
    retry_delay = 3  # Задержка между попытками (в секундах)

    for attempt in range(max_retries):
        try:
            # Отправляем запрос к API DeepSeek
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=user_context,
                stream=False
            )

            # Проверяем, что ответ существует и содержит выборки
            if not hasattr(response, 'choices') or not response.choices:
                raise ValueError("Пустой или некорректный ответ от API DeepSeek")

            # Извлекаем ответ модели
            answer = response.choices[0].message.content.strip()
            if not answer:
                raise ValueError("Ответ от API DeepSeek пуст")

            # Добавляем ответ бота в контекст
            user_context.append({"role": "assistant", "content": answer})

            # Обновляем контекст в базе данных
            update_user_context(user_id, user_context)

            # Разбиваем ответ на части, если он слишком длинный
            max_length = 4096  # Максимальная длина сообщения в Telegram
            for i in range(0, len(answer), max_length):
                chunk = answer[i:i + max_length].strip()
                if chunk:  # Проверяем, что часть не пустая
                    await update.message.reply_text(chunk)

            break  # Выходим из цикла, если всё прошло успешно

        except ValueError as e:
            # Логгируем ошибку и информируем пользователя
            logger.error(f"Ошибка при обработке ответа от API (попытка {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                await update.message.reply_text('Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.')

        except Exception as api_error:
            # Логгируем ошибку и информируем пользователя о временном сбое API
            logger.error(f"Ошибка при запросе к API DeepSeek (попытка {attempt + 1}): {api_error}")
            if attempt == max_retries - 1:
                await update.message.reply_text('Временная ошибка API. Пожалуйста, попробуйте позже.')
            else:
                logger.warning(f"Повторная попытка ({attempt + 2}/{max_retries}) после ошибки: {api_error}")
                time.sleep(retry_delay)

# Основная функция для запуска бота
def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрируем обработчики команд, сообщений и документов
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()