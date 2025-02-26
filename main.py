import os
import asyncio
import io
import json
import aiohttp
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Конфигурация
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FLUX_API_KEY = os.getenv("FLUX_API_KEY")
API_URL = "https://api.gen-api.ru/api/v1/networks/flux"  # Эндпоинт для создания задачи

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"Bearer {FLUX_API_KEY}"
}

# Модель и параметры по умолчанию
DEFAULT_MODEL = "Realism"  # Модель для генерации изображений
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 1280
DEFAULT_NUM_IMAGES = 1
DEFAULT_NUM_INFERENCE_STEPS = 28
DEFAULT_GUIDANCE_SCALE = 5
DEFAULT_STRENGTH = 1
DEFAULT_SAFETY_CHECKER = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    await update.message.reply_text(
        "Привет! Отправьте текстовый промт для генерации изображения. "
        "Например: 'Портрет женщины в стиле бохо с зелеными глазами.'"
    )

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений для генерации изображения."""
    prompt = update.message.text.strip()
    if not prompt:
        await update.message.reply_text("Пожалуйста, введите промт.")
        return

    # Формируем тело запроса
    input_data = {
        "translate_input": True,  # Автоматический перевод промта
        "prompt": prompt,
        "model": DEFAULT_MODEL,
        "width": DEFAULT_WIDTH,
        "height": DEFAULT_HEIGHT,
        "num_inference_steps": DEFAULT_NUM_INFERENCE_STEPS,
        "guidance_scale": DEFAULT_GUIDANCE_SCALE,
        "num_images": DEFAULT_NUM_IMAGES,
        "enable_safety_checker": DEFAULT_SAFETY_CHECKER,
        "strength": DEFAULT_STRENGTH,
        "is_sync": False  # Асинхронный режим
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Отправка запроса на создание задачи
            async with session.post(API_URL, json=input_data, headers=HEADERS) as resp:
                resp.raise_for_status()
                task_data = await resp.json()
                print("Ответ API (создание задачи):", json.dumps(task_data, indent=4, ensure_ascii=False))

                # Получаем request_id из ответа
                request_id = task_data.get("request_id")
                if not request_id:
                    await update.message.reply_text("Ошибка: не удалось получить request_id.")
                    return

                await update.message.reply_text("Генерация изображения началась. Ожидайте...")

            # Ожидание завершения задачи
            result_url = f"https://api.gen-api.ru/api/v1/requests/{request_id}"
            image_url = None

            # Проверяем статус задачи несколько раз с интервалом
            for attempt in range(10):  # 10 попыток с интервалом 15 секунд
                await asyncio.sleep(15)
                async with session.get(result_url, headers=HEADERS) as result_resp:
                    result_resp.raise_for_status()
                    result_data = await result_resp.json()
                    print(f"Попытка {attempt + 1}. Ответ API (статус задачи):",
                          json.dumps(result_data, indent=4, ensure_ascii=False))

                    status = result_data.get("status")
                    if status == "completed":
                        image_url = result_data.get("output", [])[0]  # Получаем первый URL из списка
                        break
                    elif status == "failed":
                        await update.message.reply_text("Ошибка генерации изображения (статус failed).")
                        return
            else:
                await update.message.reply_text("Время ожидания истекло.")
                return

            # Скачиваем изображение
            async with session.get(image_url) as img_resp:
                img_resp.raise_for_status()
                image_data = await img_resp.read()

            # Отправляем изображение пользователю
            await update.message.reply_photo(photo=InputFile(io.BytesIO(image_data), filename="image.png"))

    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {str(e)}")

if __name__ == "__main__":
    # Создаем и запускаем приложение
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image))
    app.run_polling()
