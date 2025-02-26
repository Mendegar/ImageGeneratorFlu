import os
import io
import requests
import asyncio
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
    await update.message.reply_text("Привет! Отправь промт для генерации изображения.")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text.strip()
    if not prompt:
        await update.message.reply_text("Введите промт.")
        return

    # Тело запроса как в документации
    input_data = {
        "callback_url": None,
        "prompt": prompt
    }

    try:
        # 1. Создаем задачу
        response = requests.post(API_URL, json=input_data, headers=HEADERS)
        response.raise_for_status()
        task_data = response.json()
        print("Создана задача:", task_data)

        request_id = task_data["request_id"]
        await update.message.reply_text("Генерация началась. Ожидайте...")

        # 2. Проверяем статус
        result_url = f"https://api.gen-api.ru/api/v1/requests/{request_id}"
        image_url = None
        
        for _ in range(10):  # 10 попыток
            await asyncio.sleep(15)
            result_response = requests.get(result_url, headers=HEADERS)
            result_data = result_response.json()
            print("Статус задачи:", result_data)

            if result_data["status"] == "success":
                image_url = result_data["output"]  # URL изображения
                break
            elif result_data["status"] == "failed":
                await update.message.reply_text("Ошибка генерации.")
                return
        else:
            await update.message.reply_text("Время ожидания истекло.")
            return

        # 3. Скачиваем и отправляем изображение
        image_response = requests.get(image_url)
        image_data = io.BytesIO(image_response.content)
        await update.message.reply_photo(photo=InputFile(image_data, filename="image.png"))

    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

if __name__ == "__main__":
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image))
    app.run_polling()
