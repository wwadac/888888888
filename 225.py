import asyncio
from datetime import datetime, timedelta
from telegram import Bot
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "7971014285:AAGe6IbdI7_dLHsn3UdGBER-wZRKK-buSys"

async def start(update, context):
    await update.message.reply_text(
        "Привет! Я бот-напоминалка. Используй команду /remind <время> <текст>\n"
        "Например: /remind 10m Сделать зарядку"
    )

async def remind(update, context):
    try:
        # Парсим аргументы
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("Ошибка: Недостаточно аргументов")
            return

        time_str = args[0].lower()
        text = " ".join(args[1:])

        # Преобразуем время в секунды
        if time_str.endswith('m'):
            minutes = int(time_str[:-1])
            delay = minutes * 60
        elif time_str.endswith('h'):
            hours = int(time_str[:-1])
            delay = hours * 3600
        else:
            await update.message.reply_text("Используйте формат: 10m (минуты) или 1h (часы)")
            return

        # Создаем задачу
        chat_id = update.effective_chat.id
        context.job_queue.run_once(
            callback=send_reminder,
            when=delay,
            data={'chat_id': chat_id, 'text': text}
        )

        await update.message.reply_text(
            f"Напоминание установлено!\n"
            f"Текст: {text}\n"
            f"Время: через {time_str}"
        )

    except (IndexError, ValueError):
        await update.message.reply_text("Ошибка в формате команды")

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.data['chat_id']
    text = job.data['text']
    
    # Отправляем 4 одинаковых сообщения
    for i in range(4):
        await context.bot.send_message(chat_id=chat_id, text=f"🔔 Напоминание: {text}")
        await asyncio.sleep(1)  # Интервал 1 секунда между сообщениями

if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("remind", remind))

    application.run_polling()
