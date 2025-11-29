import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токен бота (замени на свой)
BOT_TOKEN = "7971014285:AAFIqR_WR_w8GeK1ErOgXYK8EIcHWYhC4pI"

# Словарь для хранения счетчиков по пользователям
stepfather_count = {}

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name
    
    # Увеличиваем счетчик отчимов
    if user_id in stepfather_count:
        stepfather_count[user_id] += 1
    else:
        stepfather_count[user_id] = 1
    
    count = stepfather_count[user_id]
    
    # Формируем ответ в зависимости от количества
    if count == 1:
        message = f"🎤 {username}, у тебя 1 отчим!"
    elif 2 <= count <= 4:
        message = f"¯\_(ツ)_/¯ {username}, у тебя {count} отчима!"
    else:
        message = f"¯\_(ツ)_/¯ {username}, у тебя {count} отчимов!"
    
    await update.message.reply_text(message)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().strip()
    
    # Ответы на определенные слова
    if text == 'да':
        await update.message.reply_text("пизда")
        return
    
    if text == 'привет':
        await update.message.reply_text("сладкий")
        return
    
    # Если в тексте есть упоминание об отчимах
    if any(word in text for word in ['отчим', 'stepfather', 'сколько отчимов']):
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        count = stepfather_count.get(user_id, 0)
        
        if count == 0:
            message = f"🤔 {username}, у тебя пока нет отчимов! Отправь голосовое сообщение чтобы получить первого."
        else:
            message = f"📊 {username}, у тебя {count} отчимов!"
        
        await update.message.reply_text(message)

def main():
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчик голосовых сообщений
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    
    # Обработчик текстовых сообщений (отвечает на вопросы об отчимах)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Запускаем бота
    application.run_polling()
    print("Бот запущен...")

if __name__ == "__main__":
    main()
