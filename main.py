import os
import requests
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Конфигурация
TELEGRAM_TOKEN = os.getenv("7201915918:AAHNjGxFZf05Cf_pgxzmtQzyFTL7nH0YH38")
FLUX_API_KEY = os.getenv("FLUX_API_KEY")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь мне текстовый промпт, и я сгенерирую изображение через Flux.ai.")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    user_id = update.message.from_user.id

    # Запрос к Flux.ai API
    headers = {"Authorization": f"Bearer {FLUX_API_KEY}"}
    data = {"prompt": prompt, "width": 512, "height": 512}
    
    try:
        response = requests.post("https://api.flux.ai/v1/generate", json=data, headers=headers)
        response.raise_for_status()
        image_url = response.json()["url"]

        # Скачивание изображения
        image_data = requests.get(image_url).content
        
        # Отправка изображения в Telegram
        await update.message.reply_photo(photo=InputFile(io.BytesIO(image_data), filename="image.png"))
    
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

if __name__ == "__main__":
    # Инициализация бота
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image))
    
    # Запуск бота
    app.run_polling()
