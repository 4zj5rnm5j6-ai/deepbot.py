# DeepBot (Telegram)

Простой Telegram-бот на python-telegram-bot, использует:
- DeepSeek — для диалогов
- Tavily — для поиска
- Hugging Face — для генерации картинок
- ElevenLabs — для озвучки

Файлы:
- bot.py — основной код
- requirements.txt — зависимости
- Procfile — команда запуска для Railway
- .env.example — пример переменных окружения

Как локально:
1. Скопировать .env.example → .env и заполнить значения.
2. Установить зависимости: `python -m pip install -r requirements.txt`
3. Запустить: `python bot.py`

Деплой на Railway:
1. Создать новый GitHub-репозиторий и запушить проект.
2. В Railway → New Project → Deploy from GitHub → выбрать этот репозиторий.
3. В настройках сервиса добавить Environment Variables (TELEGRAM_TOKEN, DEEPSEEK_KEY, ...).
4. Deploy — Railway запустит `python bot.py` (через Procfile).
