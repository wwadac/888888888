import asyncio
import pandas as pd
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Замените на ваш токен бота
BOT_TOKEN = "8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk"

async def handle_excel_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, что сообщение содержит документ
    if not update.message.document:
        await update.message.reply_text("Пожалуйста, отправьте Excel файл (.xlsx)")
        return
    
    document = update.message.document
    
    # Проверяем, что это Excel файл
    if not document.file_name.endswith(('.xlsx', '.xls')):
        await update.message.reply_text("Пожалуйста, отправьте файл в формате Excel (.xlsx или .xls)")
        return
    
    try:
        # Скачиваем файл
        file = await document.get_file()
        await file.download_to_drive("temp_file.xlsx")
        
        # Читаем Excel файл
        df = pd.read_excel("temp_file.xlsx")
        
        # Ищем колонку с Telegram ссылками (обычно это первая колонка)
        # Ищем колонки, содержащие ссылки
        users = []
        for col in df.columns:
            for cell in df[col]:
                if isinstance(cell, str) and cell.startswith('https://t.me/'):
                    # Извлекаем username из ссылки
                    username = cell.split('/')[-1]
                    if username:
                        users.append(f"@{username}")
        
        # Убираем дубликаты
        users = list(set(users))
        
        if users:
            # Отправляем пользователей частями (Telegram имеет ограничение на длину сообщения)
            users_text = "\n".join(users)
            
            # Разбиваем на сообщения по 50 пользователей
            users_list = users_text.split('\n')
            for i in range(0, len(users_list), 50):
                chunk = users_list[i:i+50]
                await update.message.reply_text("\n".join(chunk))
                
            await update.message.reply_text(f"✅ Найдено {len(users)} уникальных пользователей")
        else:
            await update.message.reply_text("❌ В файле не найдены Telegram ссылки")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при обработке файла: {str(e)}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Отправь мне Excel файл, и я извлеку из него всех Telegram пользователей.\n\n"
        "Бот ищет ссылки формата: https://t.me/username"
    )

def main():
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(MessageHandler(filters.Document.ALL, handle_excel_file))
    application.add_handler(MessageHandler(filters.COMMAND & filters.Regex("start"), start_command))
    
    # Запускаем бота
    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()