ADMIN_ID = 8208248742  # Ваш Telegram user_id
from db import set_balance
# --- Админ-команды ---
@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text.startswith('/admin'))
async def admin_panel(message: types.Message):
    text = (
        "Админ-панель\n"
        "/add_balance <user_id> <amount> — добавить баланс пользователю\n"
        "/ban <user_id> — забанить пользователя\n"
        "/unban <user_id> — разбанить пользователя\n"
        "/users — список пользователей"
    )
    await message.answer(text)

# Бан-лист (в памяти, для простоты)
banned_users = set()

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text.startswith('/add_balance'))
async def add_balance_cmd(message: types.Message):
    try:
        _, uid, amount = message.text.split()
        uid = int(uid)
        amount = float(amount)
        set_balance(uid, amount)
        await message.answer(f'Баланс пользователя {uid} установлен: {amount} TON')
    except Exception as e:
        await message.answer(f'Ошибка: {e}')

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text.startswith('/ban'))
async def ban_cmd(message: types.Message):
    try:
        _, uid = message.text.split()
        uid = int(uid)
        banned_users.add(uid)
        await message.answer(f'Пользователь {uid} забанен.')
    except Exception as e:
        await message.answer(f'Ошибка: {e}')

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text.startswith('/unban'))
async def unban_cmd(message: types.Message):
    try:
        _, uid = message.text.split()
        uid = int(uid)
        banned_users.discard(uid)
        await message.answer(f'Пользователь {uid} разбанен.')
    except Exception as e:
        await message.answer(f'Ошибка: {e}')

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text.startswith('/users'))
async def users_cmd(message: types.Message):
    import sqlite3
    conn = sqlite3.connect('users.db')
    cur = conn.execute('SELECT user_id, balance FROM users')
    users = cur.fetchall()
    conn.close()
    if users:
        text = '\n'.join([f'ID: {u[0]}, Баланс: {u[1]}' for u in users])
    else:
        text = 'Нет пользователей.'
    await message.answer(text)
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

TOKEN = os.getenv("REDOCASE_BOT_TOKEN")

import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from db import init_db, get_balance, delete_user
from utils import get_ton_usdt_rate

TOKEN = os.getenv("REDOCASE_BOT_TOKEN")
if not TOKEN:
    raise SystemExit("Set REDOCASE_BOT_TOKEN environment variable with your bot token.")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

WELCOME_TEXT = (
    "🚀 RedoCase — это бот-кошелёк/криптобот для получения, отправки, покупки и хранения криптовалюты в Telegram."
    "\n\nОбо всех возможностях читай в официальном канале: https://t.me/+7KgLGnOLv8dmNDMx"
)



# Главное меню (инлайн-кнопки)
def main_menu_inline(lang='ru'):
    # Тексты на двух языках
    texts = {
        'ru': {
            'balance': '💰 Баланс',
            'deposit': '➕ Пополнить',
            'course': '📈 Курс TON/USDT',
            'ref': '👤 Партнёрка',
            'support': '🆘 Поддержка',
            'logout': '🚪 Выйти',
            'mainmenu': '🏠 В меню',
            'history': '📜 История',
            'lang': '🇬🇧 EN'
        },
        'en': {
            'balance': '💰 Balance',
            'deposit': '➕ Deposit',
            'course': '📈 TON/USDT Rate',
            'ref': '👤 Referral',
            'support': '🆘 Support',
            'logout': '🚪 Logout',
            'mainmenu': '🏠 Menu',
            'history': '📜 History',
            'lang': '🇷🇺 RU'
        }
    }
    t = texts[lang]
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton(t['balance'], callback_data="balance"),
        types.InlineKeyboardButton(t['deposit'], callback_data="deposit"),
        types.InlineKeyboardButton(t['course'], callback_data="course"),
        types.InlineKeyboardButton(t['history'], callback_data="history"),
        types.InlineKeyboardButton(t['ref'], callback_data="ref"),
        types.InlineKeyboardButton(t['support'], callback_data="support"),
        types.InlineKeyboardButton(t['logout'], callback_data="logout")
    )
    kb.add(
        types.InlineKeyboardButton(t['mainmenu'], callback_data="mainmenu"),
        types.InlineKeyboardButton(t['lang'], callback_data="langswitch")
    )
    return kb

# Удаление старого сообщения (если есть)
async def safe_delete(msg):
    try:
        await msg.delete()
    except Exception:
        pass


@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    if message.from_user.id in banned_users:
        await message.answer("Вы забанены.")
        return
    if message.chat.type == "private":
        await message.answer(WELCOME_TEXT, reply_markup=main_menu_inline())


# Инлайн-обработчики
from db import get_history

# Для простоты: хранить язык в памяти (на практике — в БД)
user_lang = {}

@dp.callback_query_handler(lambda c: c.data in ["balance", "deposit", "course", "ref", "support", "logout", "mainmenu", "history", "langswitch"])
async def inline_menu_handler(call: types.CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    lang = user_lang.get(user_id, 'ru')
    if call.data == "balance":
        balance = get_balance(user_id)
        text = f"Ваш баланс: {balance:.4f} TON" if lang == 'ru' else f"Your balance: {balance:.4f} TON"
        await call.message.edit_text(text, reply_markup=main_menu_inline(lang))
    elif call.data == "deposit":
        ton_addr = "UQAfR6kseWxX-cH5DzpOH-mKWn6oidyL5ynM4SGNiabU2qCJ"
        if lang == 'ru':
            text = (
                f"Для пополнения переведите TON на адрес:\n<code>{ton_addr}</code>\n\n"
                "После перевода обязательно напишите в поддержку (@YourSupport) и приложите скриншот или ссылку на транзакцию. "
                "Без подтверждения пополнение не будет зачислено!"
            )
        else:
            text = (
                f"To deposit, send TON to address:\n<code>{ton_addr}</code>\n\n"
                "After sending, be sure to contact support (@YourSupport) and attach a screenshot or transaction link. "
                "Without confirmation, the deposit will not be credited!"
            )
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_inline(lang))
    elif call.data == "course":
        ton, usdt = await get_ton_usdt_rate()
        if ton and usdt:
            text = f"Курс TON: <b>{ton} USD</b>\nКурс USDT: <b>{usdt} USD</b>" if lang == 'ru' else f"TON rate: <b>{ton} USD</b>\nUSDT rate: <b>{usdt} USD</b>"
            await call.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_inline(lang))
        else:
            text = "Не удалось получить курс. Попробуйте позже." if lang == 'ru' else "Failed to get rate. Try later."
            await call.message.edit_text(text, reply_markup=main_menu_inline(lang))
    elif call.data == "ref":
        ref_link = f"https://t.me/redocasebot?start={user_id}"
        text = f"Ваша реферальная ссылка:\n{ref_link}" if lang == 'ru' else f"Your referral link:\n{ref_link}"
        await call.message.edit_text(text, reply_markup=main_menu_inline(lang))
    elif call.data == "support":
        text = "Временно поддержка только через Telegram: @RedobotSupport" if lang == 'ru' else "Support only via Telegram: @RedobotSupport"
        await call.message.edit_text(text, reply_markup=main_menu_inline(lang))
    elif call.data == "logout":
        delete_user(user_id)
        text = "Ваши данные удалены. Для продолжения используйте /start" if lang == 'ru' else "Your data deleted. Use /start to continue."
        await call.message.edit_text(text)
    elif call.data == "mainmenu":
        await call.message.edit_text(WELCOME_TEXT if lang == 'ru' else "🚀 RedoCase — crypto wallet bot for receiving, sending, buying and storing cryptocurrency in Telegram.\n\nRead about all features in the official channel: https://t.me/+7KgLGnOLv8dmNDMx", reply_markup=main_menu_inline(lang))
    elif call.data == "history":
        hist = get_history(user_id, limit=10)
        if hist:
            if lang == 'ru':
                text = "Последние операции:\n" + "\n".join([f"{a}: {amnt} ({ts[:16]})" for a, amnt, ts in hist])
            else:
                text = "Last operations:\n" + "\n".join([f"{a}: {amnt} ({ts[:16]})" for a, amnt, ts in hist])
        else:
            text = "Нет операций." if lang == 'ru' else "No operations."
        await call.message.edit_text(text, reply_markup=main_menu_inline(lang))
    elif call.data == "langswitch":
        user_lang[user_id] = 'en' if lang == 'ru' else 'ru'
        await call.message.edit_text(WELCOME_TEXT if user_lang[user_id]=='ru' else "🚀 RedoCase — crypto wallet bot for receiving, sending, buying and storing cryptocurrency in Telegram.\n\nRead about all features in the official channel: https://t.me/+7KgLGnOLv8dmNDMx", reply_markup=main_menu_inline(user_lang[user_id]))

# Команда /balance
@dp.message_handler(commands=["balance"])
async def balance_handler(message: types.Message):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    await message.answer(f"Ваш баланс: {balance:.4f} TON")


if __name__ == "__main__":
    init_db()
    executor.start_polling(dp, skip_updates=True)
