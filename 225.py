import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Включим логирование, чтобы видеть ошибки
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Ваш токен от BotFather
API_TOKEN = '7971014285:AAGe6IbdI7_dLHsn3UdGBER-wZRKK-buSys'

# ID администратора (узнать можно, написав боту /start, а затем посмотрев логи)
ADMIN_CHAT_ID = 8191068380

# Хранилище для состояний пользователей (в реальном проекте используйте БД)
user_sessions = {}

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    # Это симуляция приветственного сообщения для нового пользователя
    welcome_text = f"""
    👋 Добро пожаловать, {user_name}!

    Это тестовый бот для бизнес-аккаунта. Чем я могу вам помочь?

    *Доступные команды:*
    /menu - Посмотреть наше меню (Быстрый ответ)
    /price - Узнать прайс-лист
    /operator - Связаться с живым оператором
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

    # Логируем нового пользователя
    logging.info(f"Новый пользователь: {user_name} (ID: {user_id})")

# Команда /menu (Быстрый ответ)
async def quick_reply_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu_text = """
    🍽️ *Наше меню*

    *Первые блюда*
    • Борщ - 300 руб.
    • Солянка - 350 руб.

    *Вторые блюда*
    • Стейк - 700 руб.
    • Паста - 450 руб.

    *Напитки*
    • Кофе - 150 руб.
    • Сок - 100 руб.

    Выберите блюдо и напишите нам номер!
    """
    # Можно также прикрепить файл (menu.pdf)
    # await update.message.reply_document(document=open('menu.pdf', 'rb'))
    await update.message.reply_text(menu_text, parse_mode='Markdown')

# Команда /price (Еще один быстрый ответ)
async def quick_reply_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price_text = "Спасибо за интерес! Актуальный прайс-лист во вложении."
    await update.message.reply_text(price_text)
    # Вместо этого можно отправить файл
    # await update.message.reply_document(document=open('price.pdf', 'rb'))

# Команда /operator
async def call_operator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    # Сообщение пользователю
    await update.message.reply_text("🔄 Ожидайте, мы соединяем вас с оператором...")

    # Уведомление администратору
    operator_text = f"🚨 *Запрос на связь с оператором!*\\nПользователь: {user_name} \\nID: `{user_id}`"
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=operator_text,
        parse_mode='Markdown'
    )

# Обработка всех текстовых сообщений (основной AI/автоответчик)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.lower()
    user_id = update.effective_user.id

    # Простейший "искусственный интеллект" на основе ключевых слов
    if any(word in user_message for word in ['цена', 'стоит', 'сколько']):
        response = "Информацию о ценах вы можете посмотреть в нашем прайсе: /price"
    elif any(word in user_message for word in ['меню', 'еда', 'блюд']):
        response = "С нашим меню вы можете ознакомиться здесь: /menu"
    elif any(word in user_message for word in ['оператор', 'человек', 'связь']):
        response = "Чтобы связаться с оператором, используйте команду /operator"
    elif any(word in user_message for word in ['привет', 'здравствуй', 'начать']):
        response = "С возвращением! Чем я могу вам помочь? Используйте команды /menu или /price для быстрого доступа к информации."
    else:
        response = "Извините, я еще учусь. Пока я могу ответить на вопросы о ценах, меню или соединить с оператором. Попробуйте использовать команды из меню."

    await update.message.reply_text(response)

# Основная функция
def main():
    # Создаем приложение и передаем ему токен
    application = Application.builder().token(API_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", quick_reply_menu))
    application.add_handler(CommandHandler("price", quick_reply_price))
    application.add_handler(CommandHandler("operator", call_operator))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()
