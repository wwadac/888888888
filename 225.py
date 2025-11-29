import logging
import random
import requests
import json
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токены
BOT_TOKEN = "7971014285:AAFIqR_WR_w8GeK1ErOgXYK8EIcHWYhC4pI"
DEEPSEEK_API_KEY = "sk-c7de6f151629444a8a85020bea2f04d6"

# Словарь для хранения счетчиков по пользователям
stepfather_count = {}

async def generate_roast(target_name: str) -> str:
    """Генерирует подъёб через DeepSeek API"""
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        prompt = f"""Придумай короткий и едкий подъёб (до 4 слов максимум) для человека по имени {target_name}. 
        Подъёб должен быть смешным, но не слишком оскорбительным. Только сам подъёб, без лишних слов."""
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Ты мастер коротких и едких подъёбов. Отвечай только самим подъёбом."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 20,
            "temperature": 0.8
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        roast = result["choices"][0]["message"]["content"].strip()
        
        # Обрезаем до 4 слов если нужно
        words = roast.split()
        if len(words) > 4:
            roast = ' '.join(words[:4])
            
        return roast
        
    except Exception as e:
        logging.error(f"Ошибка генерации подъёба: {e}")
        # Фолбэк подъёбы если API не работает
        fallback_roasts = [
            "Отчим плачет",
            "Мама шлет привет",
            "Иди нахуй дружок",
            "Ты конченый вообще",
            "Голова бубен",
            "Рот закрой"
        ]
        return random.choice(fallback_roasts)

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
    user = update.effective_user
    username = user.username or user.first_name
    
    # Ответы на определенные слова
    if text == 'да':
        await update.message.reply_text("пизда")
        return
    
    if text == 'привет':
        await update.message.reply_text("сладкий")
        return
    
    # Подъёб при упоминании бота или по триггерам
    if any(word in text for word in ['бот', 'bot', 'отчим', 'stepfather', 'сколько отчимов']):
        user_id = user.id
        
        # С шансом 30% отправить подъёб
        if random.random() < 0.3:
            roast = await generate_roast(username)
            await update.message.reply_text(f"{username}, {roast}")
            return
        
        count = stepfather_count.get(user_id, 0)
        
        if count == 0:
            message = f"🤔 {username}, у тебя пока нет отчимов! Отправь голосовое сообщение чтобы получить первого."
        else:
            message = f"📊 {username}, у тебя {count} отчимов!"
        
        await update.message.reply_text(message)
        return
    
    # Случайный подъёб (шанс 10% на любое сообщение)
    if random.random() < 0.1:
        roast = await generate_roast(username)
        await update.message.reply_text(f"{username}, {roast}")

def main():
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчик голосовых сообщений
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Запускаем бота
    application.run_polling()
    print("Бот запущен...")

if __name__ == "__main__":
    main()
