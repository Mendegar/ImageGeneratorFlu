import os
import requests
import asyncio
import io
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Конфигурация
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FLUX_API_KEY = os.getenv("FLUX_API_KEY")
API_URL = "https://api.gen-api.ru/api/v1/networks/flux"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"Bearer {FLUX_API_KEY}"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    await update.message.reply_text("Привет! Отправьте промт текстом.")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик генерации изображения."""
    prompt = update.message.text
    # Минимальный набор параметров согласно документации
    input_data = {
        "callback_url": None,
        "prompt": prompt
    }
    try:
        # Отправка запроса на генерацию
        response = requests.post(API_URL, json=input_data, headers=HEADERS)
        response.raise_for_status()
        task_data = response.json()
        
        request_id = task_data.get("request_id")
        if not request_id:
            raise ValueError("Не удалось получить request_id из ответа API")
        
        await update.message.reply_text("Генерация изображения началась. Ожидайте...")
        # Получение результата по request_id
        result_url = f"https://api.gen-api.ru/api/v1/request/get/{request_id}"
        while True:
            await asyncio.sleep(10)  # ожидание 10 секунд между проверками
            result_response = requests.get(result_url, headers=HEADERS)
            result_response.raise_for_status()
            result_data = result_response.json()
            
            status = result_data.get("status")
            if status == "success":
                output = result_data.get("output")
                if not output:
                    raise ValueError("Ключ 'output' отсутствует в ответе API")
                break
            elif status == "failed":
                raise ValueError("Ошибка генерации изображения")
        
        # Скачивание изображения по URL из output
        image_response = requests.get(output)
        image_response.raise_for_status()
        image_data = image_response.content

        await update.message.reply_photo(photo=InputFile(io.BytesIO(image_data), filename="image.png"))
        
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

if __name__ == "__main__":
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image))
    app.run_polling()
