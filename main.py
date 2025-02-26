import os
import requests
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Конфигурация
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FLUX_API_KEY = os.getenv("FLUX_API_KEY")  

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь мне текстовый промпт, и я сгенерирую изображение через Flux.ai.")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text

    # Запрос к API
    headers = {"Authorization": f"Bearer {FLUX_API_KEY}"}
    data = {"prompt": prompt, "width": 512, "height": 512}
    
    try:
        response = requests.post("https://api.gen-api.ru/api/v1/networks/flux", json=data, headers=headers)
        response.raise_for_status()

        # Если API возвращает изображение напрямую
        if response.headers.get("Content-Type", "").startswith("image/"):
            image_data = response.content
        else:
            # Если API возвращает JSON с ссылкой
            image_url = response.json().get("url")
            if not image_url:
                raise ValueError("Ключ 'url' отсутствует в ответе API")
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
