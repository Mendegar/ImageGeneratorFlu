import os
import requests
import time
import logging
import io
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    await update.message.reply_text("Привет! Отправь мне текстовый промпт, и я сгенерирую изображение через Flux.ai.")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    input_data = {"prompt": prompt, "callback_url": None}
    
    try:
        logging.info(f"Отправка запроса в Flux API: {input_data}")
        response = requests.post(API_URL, json=input_data, headers=HEADERS)
        logging.info(f"Ответ от Flux API: {response.status_code}, {response.text}")
        response.raise_for_status()
        
        task_data = response.json()
        request_id = task_data.get("request_id")
        if not request_id:
            raise ValueError("Flux API не вернул request_id")
        
        await update.message.reply_text("Генерация изображения началась. Ожидайте...")
        result_url = f"{API_URL}/{request_id}"
        
        while True:
            time.sleep(5)
            result_response = requests.get(result_url, headers=HEADERS)
            logging.info(f"Проверка статуса: {result_response.status_code}, {result_response.text}")
            result_response.raise_for_status()
            result_data = result_response.json()
            
            if result_data.get("status") == "success":
                output = result_data.get("output")
                if not output:
                    raise ValueError("Flux API не вернул output")
                break
            elif result_data.get("status") == "failed":
                raise ValueError("Flux API не смог сгенерировать изображение")
        
        image_data = requests.get(output).content
        await update.message.reply_photo(photo=InputFile(io.BytesIO(image_data), filename="image.png"))
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе к Flux API: {e}")
        await update.message.reply_text(f"Ошибка API: {str(e)}")
    except Exception as e:
        logging.error(f"Общая ошибка: {e}")
        await update.message.reply_text(f"Ошибка: {str(e)}")

if __name__ == "__main__":
    logging.info("Запуск Telegram-бота")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image))
    
    try:
        app.run_polling()
    except Exception as e:
        logging.error(f"Ошибка запуска бота: {e}")
