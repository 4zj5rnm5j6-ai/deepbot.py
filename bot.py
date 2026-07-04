import os
import requests
import json
import base64
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import logging

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== API-ключи из переменных окружения =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")
TAVILY_KEY = os.getenv("TAVILY_KEY")
HF_KEY = os.getenv("HF_KEY")  # Hugging Face для картинок
ELEVENLABS_KEY = os.getenv("ELEVENLABS_KEY")
PERSONALITY = os.getenv("PERSONALITY", "Ты — дружелюбный и остроумный помощник, отвечаешь кратко и на русском.")

# ===== Функции для работы с API =====
def detect_intent(text: str) -> str:
    keywords = {
        "search": ["найди", "поищи", "что нового", "узнай", "погода", "новости"],
        "image": ["нарисуй", "покажи", "картинку", "изображение", "сгенерируй"],
        "voice": ["озвучь", "прочитай", "скажи голосом"]
    }
    text_lower = text.lower()
    for intent, words in keywords.items():
        if any(word in text_lower for word in words):
            return intent
    return "chat"

def chat_with_deepseek(text: str) -> str:
    if not DEEPSEEK_KEY:
        return "❌ Ошибка: не указан API-ключ DeepSeek"
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": PERSONALITY},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"⚠️ Ошибка DeepSeek: {response.status_code}"
    except Exception as e:
        return f"⚠️ Ошибка: {str(e)}"

def search_internet(query: str) -> str:
    if not TAVILY_KEY:
        return "❌ Ошибка: не указан API-ключ Tavily"
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": TAVILY_KEY, "query": query, "search_depth": "basic", "max_results": 3},
            timeout=30
        )
        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                answer = f"🔍 По запросу «{query}»:\n\n"
                for i, res in enumerate(results[:3], 1):
                    answer += f"{i}. {res.get('title', 'Без заголовка')}\n   {res.get('content', '')[:200]}...\n   📎 {res.get('url', '')}\n\n"
                return answer
            return "🔍 Ничего не найдено."
        return f"⚠️ Ошибка Tavily: {response.status_code}"
    except Exception as e:
        return f"⚠️ Ошибка: {str(e)}"

def generate_image(prompt: str) -> str:
    if not HF_KEY:
        return "❌ Ошибка: не указан API-ключ Hugging Face"
    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5",
            headers={"Authorization": f"Bearer {HF_KEY}"},
            json={"inputs": prompt},
            timeout=60
        )
        if response.status_code == 200:
            return response.content  # возвращаем бинарные данные картинки
        return f"⚠️ Ошибка генерации: {response.status_code}"
    except Exception as e:
        return f"⚠️ Ошибка: {str(e)}"

def text_to_speech(text: str) -> bytes:
    if not ELEVENLABS_KEY:
        return None
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4L4X2NcvN6m2")  # Rachel
    try:
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_KEY},
            json={"text": text, "model_id": "eleven_monolingual_v1", "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}},
            timeout=30
        )
        if response.status_code == 200:
            return response.content
        return None
    except Exception:
        return None

# ===== Команды и обработчики Telegram =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💬 Поговорить", callback_data="chat")],
        [InlineKeyboardButton("🔍 Поиск", callback_data="search")],
        [InlineKeyboardButton("🎨 Картинка", callback_data="image")],
        [InlineKeyboardButton("🎤 Голос", callback_data="voice")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Привет! Я — твой мультимедийный ассистент.\n\n"
        "Просто напиши мне что угодно, или выбери режим с помощью кнопок:",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text:
        return
    
    # Отправляем "печатает..."
    await update.message.chat.send_action(action="typing")
    
    intent = detect_intent(user_text)
    
    # Короткие команды (если пользователь пишет просто "поиск")
    if user_text.lower() in ["поиск", "найди"]:
        await update.message.reply_text("🔍 Напишите, что я должен найти.")
        return
    if user_text.lower() in ["картинка", "нарисуй"]:
        await update.message.reply_text("🎨 Напишите, что я должен нарисовать.")
        return
    if user_text.lower() in ["голос", "озвучь"]:
        await update.message.reply_text("🎤 Напишите текст, который я озвучу.")
        return
    
    # Обработка по намерению
    if intent == "search":
        result = search_internet(user_text)
        await update.message.reply_text(result, parse_mode="Markdown")
    elif intent == "image":
        await update.message.reply_text("🎨 Генерирую картинку, это может занять до минуты...")
        image_data = generate_image(user_text)
        if isinstance(image_data, bytes):
            await update.message.reply_photo(photo=image_data, caption=f"🖼️ «{user_text}»")
        else:
            await update.message.reply_text(image_data)
    elif intent == "voice":
        await update.message.reply_text("🎤 Генерирую голосовое сообщение...")
        audio_data = text_to_speech(user_text)
        if audio_data:
            await update.message.reply_voice(voice=audio_data, caption="🗣️ Ваш текст озвучен")
        else:
            await update.message.reply_text("❌ Не удалось озвучить текст (проверьте ключ ElevenLabs).")
    else:
        # Обычный диалог
        answer = chat_with_deepseek(user_text)
        await update.message.reply_text(answer, parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    messages = {
        "chat": "💬 Просто напишите мне что угодно, я отвечу.",
        "search": "🔍 Напишите поисковый запрос (например, «погода в Москве»).",
        "image": "🎨 Напишите, что я должен нарисовать.",
        "voice": "🎤 Напишите текст для озвучки."
    }
    await query.edit_message_text(messages.get(action, "Выберите действие:"))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Мои возможности:*\n\n"
        "• *Обычный диалог* — просто напиши сообщение\n"
        "• *Поиск* — напиши «найди ...» или «поищи ...»\n"
        "• *Картинка* — напиши «нарисуй ...» или «покажи ...»\n"
        "• *Голос* — напиши «озвучь ...» или «скажи голосом ...»\n\n"
        "Используй кнопки для быстрой смены режима!",
        parse_mode="Markdown"
    )

# ===== Запуск =====

def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("❌ Ошибка: не указан TELEGRAM_TOKEN в переменных окружения")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("🤖 Бот запущен и готов к работе!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
