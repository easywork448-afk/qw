# RedoCase Telegram Bot

Внимание: ваш токен был опубликован в сообщении — он скомпрометирован. Сразу перегенерируйте токен через @BotFather и НЕ публикуйте его публично.

Файлы:
- bot.py
- requirements.txt

Переменная окружения (обязательно): REDOCASE_BOT_TOKEN — новый токен вашего бота.

Установка и запуск (Windows PowerShell):

```powershell
python -m pip install -r requirements.txt
$Env:REDOCASE_BOT_TOKEN = "YOUR_NEW_TOKEN"
python bot.py
```

Или в CMD:

```cmd
pip install -r requirements.txt
set REDOCASE_BOT_TOKEN=YOUR_NEW_TOKEN
python bot.py
```

Описание: при команде /start бот отправляет приветственный текст и кнопку с ссылкой на официальный канал.
