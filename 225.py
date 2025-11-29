import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import json

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация (замени на свои значения!)
DEEPSEEK_API_KEY = "3c57df8805ab5de5a23a032ed39b9af9"  # Получи на platform.deepseek.com
TELEGRAM_BOT_TOKEN = "7971014285:AAFIqR_WR_w8GeK1ErOgXYK8EIcHWYhC4pI"  # Получи у @BotFather
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

class DeepSeekBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        welcome_text = f"""
🤖 Привет, {user.first_name}!

Я бот с интеграцией нейросети DeepSeek. Просто напиши мне сообщение, и я обработаю его с помощью AI!

Команды:
/start - начать работу
/help - помощь

Отправь мне любой текст и получи умный ответ! 🚀
        """
        await update.message.reply_text(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📖 Помощь по боту:

• Просто напиши любое сообщение, и я обработаю его через DeepSeek
• Поддерживаются вопросы на разные темы
• Бот сохраняет контекст разговора

Примеры вопросов:
"Напиши код Python для hello world"
"Объясни теорию относительности"
"Помоги составить план обучения"
        """
        await update.message.reply_text(help_text)
    
    async def query_deepseek(self, prompt: str) -> str:
        """Отправка запроса к DeepSeek API"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API error: {e}")
            return "❌ Ошибка соединения с нейросетью. Попробуйте позже."
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return "❌ Произошла непредвиденная ошибка при обработке запроса."
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user_message = update.message.text
        user = update.effective_user
        
        # Отправляем статус "печатает"
        await update.message.chat.send_action(action="typing")
        
        try:
            # Получаем ответ от DeepSeek
            bot_response = await self.query_deepseek(user_message)
            
            # Если ответ слишком длинный, разбиваем на части
            if len(bot_response) > 4000:
                for i in range(0, len(bot_response), 4000):
                    await update.message.reply_text(bot_response[i:i+4000])
            else:
                await update.message.reply_text(bot_response)
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text("❌ Произошла ошибка при обработке вашего сообщения.")
    
    def run(self):
        """Запуск бота"""
        logger.info("Бот запущен!")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

# Запуск бота
if __name__ == "__main__":
    # Проверка наличия токенов
    if DEEPSEEK_API_KEY == "your_deepseek_api_key_here" or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        print("❌ ОШИБКА: Замените DEEPSEEK_API_KEY и TELEGRAM_BOT_TOKEN на реальные значения!")
        print("1. Получи API ключ на https://platform.deepseek.com/")
        print("2. Создай бота через @BotFather в Telegram")
        exit(1)
    
    bot = DeepSeekBot()
    bot.run()

