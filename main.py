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
        await update.message.reply_text("Пожалуйста, введите ненулевой промт.")
        return

    # Отправляем минимальный запрос: только prompt (без callback_url)
    input_data = {
        "prompt": prompt
    }
    
    try:
        # Запрос на генерацию изображения
        response = requests.post(API_URL, json=input_data, headers=HEADERS)
        if response.status_code != 200:
            await update.message.reply_text(f"Ошибка API {response.status_code}: {response.text}")
            return
        task_data = response.json()
        print("Ответ API на запрос генерации:", json.dumps(task_data, indent=4, ensure_ascii=False))
        
        request_id = task_data.get("request_id")
        if not request_id:
            await update.message.reply_text("Не удалось получить request_id из ответа API.")
            return
        
        await update.message.reply_text("Генерация изображения началась. Ожидайте...")
        result_url = f"https://api.gen-api.ru/api/v1/request/get/{request_id}"
        for _ in range(10):  # максимум 10 попыток по 10 секунд
            await asyncio.sleep(10)
            result_response = requests.get(result_url, headers=HEADERS)
            if result_response.status_code != 200:
                await update.message.reply_text(
                    f"Ошибка при получении результата: {result_response.status_code} {result_response.text}"
                )
                return
            result_data = result_response.json()
            print("Ответ API на проверку результата:", json.dumps(result_data, indent=4, ensure_ascii=False))
            status = result_data.get("status")
            if status == "success":
                output = result_data.get("output")
                if not output:
                    await update.message.reply_text("Ключ 'output' отсутствует в ответе API.")
                    return
                break
            elif status == "failed":
                await update.message.reply_text("Ошибка генерации изображения (статус failed).")
                return
        else:
            await update.message.reply_text("Время ожидания истекло.")
            return
        
        # Скачивание изображения по URL из output
        image_response = requests.get(output)
        if image_response.status_code != 200:
            await update.message.reply_text(
                f"Ошибка при скачивании изображения: {image_response.status_code}"
            )
            return
        image_data = image_response.content
        await update.message.reply_photo(photo=InputFile(io.BytesIO(image_data), filename="image.png"))
        
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

if __name__ == "__main__":
    # Важно: убедитесь, что бот запущен только в одном экземпляре
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image))
    app.run_polling()
