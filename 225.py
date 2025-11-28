import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue # Импортируем JobQueue
from datetime import datetime, timedelta

# --- 1. Настройки и Логирование ---

# Замените 'ВАШ_ТОКЕН_БОТА' на токен, полученный от @BotFather
# Ваш токен скрыт в коде, но здесь оставлен как пример
TOKEN = "7971014285:AAGe6IbdI7_dLHsn3UdGBER-wZRKK-buSys"

# Настройка логирования, чтобы видеть ошибки в консоли
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- 2. Функция отправки 4-х напоминаний (используется Job) ---

async def send_reminder_4_times(context: ContextTypes.DEFAULT_TYPE):
    """
    Функция-обработчик JobQueue, которая отправляет сообщение 4 раза.
    Данные (chat_id, task_text) извлекаются из context.job.data.
    """
    job_data = context.job.data
    chat_id = job_data['chat_id']
    task_text = job_data['task_text']
    
    logger.info(f"Начинается отправка 4 напоминаний для чата {chat_id}: {task_text}")
    
    for i in range(1, 5):
        # Отправляем сообщение с номером попытки
        message = f"🔔 НАПОМИНАНИЕ (Попытка {i}/4):\n{task_text}"
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"Отправлено напоминание {i}/4.")
        except Exception as e:
            logger.error(f"Не удалось отправить напоминание {i}/4 в чат {chat_id}: {e}")
            break # Прерываем, если не удалось отправить
        
        # Ждем 60 секунд (1 минута) перед следующей отправкой, если это не последнее сообщение
        if i < 4:
            await asyncio.sleep(60)
            
    logger.info(f"4 напоминания отправлены и завершены для чата {chat_id}.")


# --- 3. Обработчик команды /remind ---

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /remind [ЧАС:МИНУТА] [Текст задачи]"""
    chat_id = update.effective_chat.id
    
    # 1. Проверяем формат команды
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Неверный формат команды.\n"
            "Используйте: /remind ЧАС:МИНУТА Текст задачи\n"
            "Пример: /remind 15:30 Забрать посылку"
        )
        return

    time_str = context.args[0]
    task_text = " ".join(context.args[1:])
    
    try:
        # 2. Парсим время
        reminder_hour, reminder_minute = map(int, time_str.split(':'))
        
        # 3. Вычисляем время напоминания
        now = datetime.now()
        # Создаем целевое время на сегодня
        target_time = now.replace(hour=reminder_hour, minute=reminder_minute, second=0, microsecond=0)
        
        # Если указанное время уже прошло сегодня, устанавливаем на завтра
        if target_time <= now:
            target_time += timedelta(days=1)

        delay_seconds = (target_time - now).total_seconds()
        
        # 4. Планируем задачу с помощью JobQueue.run_once()
        
        context.job_queue.run_once(
            send_reminder_4_times, 
            delay_seconds, 
            data={'chat_id': chat_id, 'task_text': task_text},
            name=f"reminder_{chat_id}_{target_time.timestamp()}"
        )
        
        
        await update.message.reply_text(
            f"✅ Напоминание установлено!\n"
            f"Задача: **{task_text}**\n"
            f"Время: **{target_time.strftime('%H:%M %d.%m.%Y')}**\n\n"
            "Бот отправит вам 4 сообщения с интервалом в 1 минуту."
        )

    except ValueError:
        await update.message.reply_text("❌ Ошибка при парсинге времени. Убедитесь, что формат ЧАС:МИНУТА (например, 15:30).")
    except Exception as e:
        logger.error(f"Произошла ошибка при установке напоминания: {e}")
        await update.message.reply_text("❌ Произошла непредвиденная ошибка при установке напоминания.")


# --- 4. Обработчик команды /start ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение."""
    await update.message.reply_text(
        "👋 Привет! Я бот-напоминалка.\n"
        "Чтобы установить напоминание, используйте команду:\n"
        "`/remind ЧАС:МИНУТА Текст задачи`\n\n"
        "**Пример:** `/remind 11:45 Сдать отчёт`\n\n"
        "Я отправлю напоминание 4 раза, чтобы вы его точно не пропустили!"
    )


# --- 5. Основная функция запуска бота ---

def main() -> None:
    """Запускает бота."""
    # Создаем Application
    # 1. Создаем JobQueue
    job_queue = JobQueue()

    # 2. Создаем Application, передавая JobQueue
    application = Application.builder().token(TOKEN).concurrent_updates(True).job_queue(job_queue).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("remind", set_reminder))

    # Запускаем опрос сервера Telegram (бот начинает работать)
    print("Бот запущен и ожидает команд...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
