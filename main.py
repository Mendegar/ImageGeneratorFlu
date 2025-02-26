import os
import requests
import time
import io
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Конфигурация
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # Токен Telegram-бота
FLUX_API_KEY = os.getenv("FLUX_API_KEY")      # API-ключ Flux.ai

# URL API
API_URL = "https://api.gen-api.ru/api/v1/networks/flux"

# Заголовки для запросов
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"Bearer {FLUX_API_KEY}"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    await update.message.reply_text(
        "Пришлите промт текстом"
    )

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик генерации изображения."""
    prompt = update.message.text

    # Параметры для генерации
    input_data = {
        "translate_input": True,
        "prompt": prompt,
        "model": "ultra",
        "width": "2048",
        "height": "2048",
        "num_inference_steps": 28,
        "guidance_scale": 5,
        "num_images": 1,
        "enable_safety_checker": False,
        "strength": 1,
        "is_sync": False
    }

    try:
        # Отправка запроса на генерацию
        response = requests.post(API_URL, json=input_data, headers=HEADERS)
        response.raise_for_status()
        task_data = response.json()

        # Получение request_id
        request_id = task_data.get("request_id")
        if not request_id:
            raise ValueError("Не удалось получить request_id из ответа API")

        # Ожидание завершения задачи
        await update.message.reply_text("Генерация изображения началась. Ожидайте...")
        result_url = f"https://api.gen-api.ru/api/v1/request/get/{request_id}"
        while True:
            time.sleep(20)  # Ожидание 10 секунд перед проверкой статуса
            result_response = requests.get(result_url, headers=HEADERS)
            result_response.raise_for_status()
            result_data = result_response.json()

            if result_data.get("status") == "success":
                output = result_data.get("output")
                if not output:
                    raise ValueError("Ключ 'output' отсутствует в ответе API")
                break
            elif result_data.get("status") == "failed":
                raise ValueError("Ошибка генерации изображения")

        # Скачивание изображения
        image_data = requests.get(output).content

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
