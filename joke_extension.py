# Add /joke command (random joke generator)

def _fetch_joke_sync() -> str:
    """
    Синхронно запрашивает случайную шутку с https://v2.jokeapi.dev.
    Возвращает строку с шуткой или сообщение об ошибке.
    """
    try:
        url = "https://v2.jokeapi.dev/joke/Any"
        params = {
            "blacklistFlags": "nsfw,sexist,racist,explicit",
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return f"⚠️ Сервис шуток вернул код {resp.status_code}"
        data = resp.json()
        if data.get("error"):
            return "⚠️ Не удалось получить шутку."
        if data.get("type") == "single":
            return data.get("joke", "😅 Пустая шутка :(")
        setup = data.get("setup", "")
        delivery = data.get("delivery", "")
        return f"{setup}\n\n{delivery}"
    except Exception as e:
        return f"⚠️ Ошибка при получении шутки: {e}"


async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Асинхронный обработчик команды /joke — не блокирует event loop.
    """
    try:
        await update.message.chat.send_action(action="typing")
    except Exception:
        pass

    joke_text = await context.application.run_in_executor(None, _fetch_joke_sync)
    await update.message.reply_text(joke_text)
