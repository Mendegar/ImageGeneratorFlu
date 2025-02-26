import os
import requests
import asyncio
import io
import json
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Конфигурация
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FLUX_API_KEY = os.getenv("FLUX_API_KEY")
# Эндпоинт для отправки запроса на выполнение задачи
API_URL = "https://api.gen-api.ru/api/v1/networks/flux"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"Bearer {FLUX_API_KEY}"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправьте промт текстом.")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text.strip()
    if not prompt:
        await update.message.reply_text("Пожалуйста, введите промт.")
        return

    # Формируем минимальный запрос согласно документации
    input_data = {
        "callback_url": None,
        "prompt": prompt
    }

    try:
        # Отправка запроса на выполнение задачи
        response = requests.post(API_URL, json=input_data, headers=HEADERS)
        response.raise_for_status()
        task_data = response.json()
        print("Ответ API (отправка задачи):", json.dumps(task_data, indent=4, ensure_ascii=False))

        # Получаем request_id из ответа
        request_id = task_data.get("request_id")
        if not request_id:
            await update.message.reply_text("Не удалось получить request_id из ответа API.")
            return

        await update.message.reply_text("Генерация изображения началась. Ожидайте...")

        # Формируем URL для получения результата
        result_url = f"https://api.gen-api.ru/api/v1/request/get/{request_id}"
        image_url = None

        # Проводим несколько попыток получения результата (например, 5 раз по 10 секунд)
        for attempt in range(5):
            await asyncio.sleep(10)
            result_response = requests.get(result_url, headers=HEADERS)
            result_response.raise_for_status()
            result_data = result_response.json()
            print(f"Попытка {attempt+1}. Ответ API (получение результата):", 
                  json.dumps(result_data, indent=4, ensure_ascii=False))
            
            status = result_data.get("status")
            if status == "success":
                image_url = result_data.get("output")
                if not image_url:
                    await update.message.reply_text("Ключ 'output' отсутствует в ответе API.")
                    return
                break
            elif status == "failed":
                await update.message.reply_text("Ошибка генерации изображения (статус failed).")
                return
        else:
            await update.message.reply_text("Время ожидания истекло.")
            return

        # Скачиваем изображение по URL, полученному в output
        image_response = requests.get(image_url)
        image_response.raise_for_status()
        image_data = image_response.content

        # Отправляем изображение пользователю
        await update.message.reply_photo(photo=InputFile(io.BytesIO(image_data), filename="image.png"))
        
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

if __name__ == "__main__":

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image))
    app.run_polling()
