
# ...инициализация bot, dp и переменных...

# ...existing code...

import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from db import init_db, get_balance, delete_user, set_balance, get_history
from utils import get_ton_usdt_rate

TOKEN = os.getenv("REDOCASE_BOT_TOKEN")
if not TOKEN:
    raise SystemExit("Set REDOCASE_BOT_TOKEN environment variable with your bot token.")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

ADMIN_ID = 8208248742  # Ваш Telegram user_id

WELCOME_TEXT = (
    "🚀 RedoCase — это бот-кошелёк/криптобот для получения, отправки, покупки и хранения криптовалюты в Telegram."
    "\n\nОбо всех возможностях читай в официальном канале: https://t.me/+7KgLGnOLv8dmNDMx"
)

def admin_menu_kb():
    kb = types.InlineKeyboardMarkup(row_width=2)
    import sqlite3
    conn = sqlite3.connect('users.db')
    cur = conn.execute('SELECT user_id FROM users')
    users = cur.fetchall()
    conn.close()
    if users:
        for u in users:
            kb.add(types.InlineKeyboardButton(f"ID: {u[0]}", callback_data=f"admin_user_{u[0]}"))
    kb.add(
        types.InlineKeyboardButton("Добавить баланс", callback_data="admin_add_balance"),
        types.InlineKeyboardButton("Бан", callback_data="admin_ban"),
        types.InlineKeyboardButton("Разбан", callback_data="admin_unban"),
        types.InlineKeyboardButton("Обновить", callback_data="admin_refresh")
    )
    return kb
@dp.message_handler(commands=["admin"])
async def admin_panel_handler(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Админ-панель:", reply_markup=admin_menu_kb())
    else:
        await message.answer("У вас нет доступа к админ-панели.")

popular_currencies = ['TON', 'USDT', 'BTC', 'ETH']
admin_balance_state = {}
active_users = set()
banned_users = set()
user_lang = {}

def main_menu_inline(lang='ru'):
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
    # Кнопки с курсами валют убраны из главного меню
    return kb
async def admin_ban_menu(call: types.CallbackQuery):
    import sqlite3
    conn = sqlite3.connect('users.db')
    cur = conn.execute('SELECT user_id FROM users')
    users = cur.fetchall()
    conn.close()
    kb = types.InlineKeyboardMarkup(row_width=2)
    for u in users:
        kb.add(types.InlineKeyboardButton(f"Забанить {u[0]}", callback_data=f"ban_user_{u[0]}"))
    await call.message.edit_text("Выберите пользователя для бана:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("ban_user_") and c.from_user.id == ADMIN_ID)
async def ban_user_action(call: types.CallbackQuery):
    uid = int(call.data.split('_')[-1])
    banned_users.add(uid)
    await call.message.edit_text(f"Пользователь {uid} забанен.", reply_markup=admin_menu_kb())

@dp.callback_query_handler(lambda c: c.data == "admin_unban" and c.from_user.id == ADMIN_ID)
async def admin_unban_menu(call: types.CallbackQuery):
    kb = types.InlineKeyboardMarkup(row_width=2)
    for uid in banned_users:
        kb.add(types.InlineKeyboardButton(f"Разбанить {uid}", callback_data=f"unban_user_{uid}"))
    await call.message.edit_text("Выберите пользователя для разбана:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("unban_user_") and c.from_user.id == ADMIN_ID)
async def unban_user_action(call: types.CallbackQuery):
    uid = int(call.data.split('_')[-1])
    banned_users.discard(uid)
    await call.message.edit_text(f"Пользователь {uid} разбанен.", reply_markup=admin_menu_kb())

@dp.callback_query_handler(lambda c: c.data == "admin_add_balance" and c.from_user.id == ADMIN_ID)
async def admin_balance_menu(call: types.CallbackQuery):
    import sqlite3
    conn = sqlite3.connect('users.db')
    cur = conn.execute('SELECT user_id FROM users')
    users = cur.fetchall()
    conn.close()
    kb = types.InlineKeyboardMarkup(row_width=2)
    for u in users:
        kb.add(types.InlineKeyboardButton(f"Баланс {u[0]}", callback_data=f"balance_user_{u[0]}"))
    await call.message.edit_text("Выберите пользователя для изменения баланса:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("balance_user_") and c.from_user.id == ADMIN_ID)
async def balance_user_action(call: types.CallbackQuery):
    uid = int(call.data.split('_')[-1])
    kb = types.InlineKeyboardMarkup(row_width=2)
    for cur in popular_currencies:
        kb.add(types.InlineKeyboardButton(cur, callback_data=f"admin_cur_{uid}_{cur}"))
    await call.message.edit_text(f"Выберите валюту для пользователя {uid}:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("admin_cur_") and c.from_user.id == ADMIN_ID)
async def admin_currency_action(call: types.CallbackQuery):
    _, _, uid, currency = call.data.split('_')
    uid = int(uid)
    admin_balance_state[call.from_user.id] = {'uid': uid, 'currency': currency}
    await call.message.edit_text(f"Введите сумму для пользователя {uid} в {currency} (например: 10.5)")

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text.replace('.', '', 1).isdigit())
async def admin_set_balance(message: types.Message):
    state = admin_balance_state.get(message.from_user.id)
    if state:
        uid = state['uid']
        currency = state['currency']
        amount = float(message.text)
        set_balance(uid, amount)
        await message.answer(f'Баланс пользователя {uid} установлен: {amount} {currency}', reply_markup=admin_menu_kb())
        admin_balance_state.pop(message.from_user.id)
    else:
        await message.answer('Сначала выберите пользователя и валюту через админ-панель.')

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

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text == "Пользователи")
async def users_cmd(message: types.Message):
    import sqlite3
    conn = sqlite3.connect('users.db')
    cur = conn.execute('SELECT user_id, balance FROM users')
    users = cur.fetchall()
    conn.close()
    tracked = '\n'.join([str(uid) for uid in active_users])
    if users:
        text = 'Пользователи из БД:\n' + '\n'.join([f'ID: {u[0]}, Баланс: {u[1]}' for u in users])
    else:
        text = 'Нет пользователей в БД.'
    text += f"\n\nПользователи, писавшие боту:\n{tracked if tracked else 'Нет активных пользователей.'}"
    await message.answer(text)

async def safe_delete(msg):
    try:
        await msg.delete()
    except Exception:
        pass

@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    active_users.add(message.from_user.id)
    uid = message.from_user.id
    try:
        get_balance(uid)
        set_balance(uid, get_balance(uid))
    except Exception:
        set_balance(uid, 0.0)
    if message.from_user.id in banned_users:
        await message.answer("Вы забанены.")
        return
    if message.chat.type == "private":
        await message.answer(WELCOME_TEXT, reply_markup=main_menu_inline())

@dp.callback_query_handler(lambda c: c.data in ["balance", "deposit", "course", "ref", "support", "logout", "mainmenu", "history", "langswitch"] or c.data.startswith("course_"))
async def inline_menu_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    if user_id in banned_users:
        await call.message.edit_text("Вы забанены.")
        return
    lang = user_lang.get(user_id, 'ru')
    if call.data == "balance":
        balance = get_balance(user_id)
        ton, usdt = await get_ton_usdt_rate()
        if ton and usdt:
            rate_text = f"\nКурс TON: <b>{ton} USD</b>\nКурс USDT: <b>{usdt} USD</b>" if lang == 'ru' else f"\nTON rate: <b>{ton} USD</b>\nUSDT rate: <b>{usdt} USD</b>"
        else:
            rate_text = ""
        text = (f"Ваш баланс: {balance:.4f} TON" if lang == 'ru' else f"Your balance: {balance:.4f} TON") + rate_text
        try:
            await call.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_inline(lang))
        except Exception as e:
            if "Message is not modified" not in str(e):
                raise
    elif call.data == "deposit":
        ton_addr = "UQAfR6kseWxX-cH5DzpOH-mKWn6oidyL5ynM4SGNiabU2qCJ"
        if lang == 'ru':
            text = (
                f"Для пополнения переведите TON на адрес:\n<code>{ton_addr}</code>\n\n"
                "После перевода обязательно напишите в поддержку (@RedoBotSupport) и приложите скриншот или ссылку на транзакцию. "
                "Без подтверждения пополнение не будет зачислено!"
            )
        else:
            text = (
                f"To deposit, send TON to address:\n<code>{ton_addr}</code>\n\n"
                "After sending, be sure to contact support (@RedoBotSupport) and attach a screenshot or transaction link. "
                "Without confirmation, the deposit will not be credited!"
            )
        try:
            await call.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_inline(lang))
        except Exception as e:
            if "Message is not modified" not in str(e):
                raise
    # Курс теперь показывается только в разделе Баланс
    elif call.data == "ref":
        ref_link = f"https://t.me/redocasebot?start={user_id}"
        text = f"Ваша реферальная ссылка:\n{ref_link}" if lang == 'ru' else f"Your referral link:\n{ref_link}"
        try:
            await call.message.edit_text(text, reply_markup=main_menu_inline(lang))
        except Exception as e:
            if "Message is not modified" not in str(e):
                raise
    elif call.data == "support":
        text = "Временно поддержка только через Telegram: @RedobotSupport" if lang == 'ru' else "Support only via Telegram: @RedobotSupport"
        try:
            await call.message.edit_text(text, reply_markup=main_menu_inline(lang))
        except Exception as e:
            if "Message is not modified" not in str(e):
                raise
    elif call.data == "logout":
        delete_user(user_id)
        text = "Ваши данные удалены. Для продолжения используйте /start" if lang == 'ru' else "Your data deleted. Use /start to continue."
        try:
            await call.message.edit_text(text)
        except Exception as e:
            if "Message is not modified" not in str(e):
                raise
    elif call.data == "mainmenu":
        try:
            await call.message.edit_text(WELCOME_TEXT if lang == 'ru' else "🚀 RedoCase — crypto wallet bot for receiving, sending, buying and storing cryptocurrency in Telegram.\n\nRead about all features in the official channel: https://t.me/+7KgLGnOLv8dmNDMx", reply_markup=main_menu_inline(lang))
        except Exception as e:
            if "Message is not modified" not in str(e):
                raise
    elif call.data == "history":
        hist = get_history(user_id, limit=10)
        if hist:
            if lang == 'ru':
                text = "Последние операции:\n" + "\n".join([f"{a}: {amnt} ({ts[:16]})" for a, amnt, ts in hist])
            else:
                text = "Last operations:\n" + "\n".join([f"{a}: {amnt} ({ts[:16]})" for a, amnt, ts in hist])
        else:
            text = "Нет операций." if lang == 'ru' else "No operations."
        try:
            await call.message.edit_text(text, reply_markup=main_menu_inline(lang))
        except Exception as e:
            if "Message is not modified" not in str(e):
                raise
    elif call.data == "langswitch":
        user_lang[user_id] = 'en' if lang == 'ru' else 'ru'
        try:
            await call.message.edit_text(WELCOME_TEXT if user_lang[user_id]=='ru' else "🚀 RedoCase — crypto wallet bot for receiving, sending, buying and storing cryptocurrency in Telegram.\n\nRead about all features in the official channel: https://t.me/+7KgLGnOLv8dmNDMx", reply_markup=main_menu_inline(user_lang[user_id]))
        except Exception as e:
            if "Message is not modified" not in str(e):
                raise
        await call.answer()

@dp.message_handler(commands=["balance"])
async def balance_handler(message: types.Message):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    await message.answer(f"Ваш баланс: {balance:.4f} TON")

if __name__ == "__main__":
    init_db()
    executor.start_polling(dp, skip_updates=True)
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

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text == "Пользователи")
async def users_cmd(message: types.Message):
    import sqlite3
    conn = sqlite3.connect('users.db')
    cur = conn.execute('SELECT user_id, balance FROM users')
    users = cur.fetchall()
    conn.close()
    tracked = '\n'.join([str(uid) for uid in active_users])
    if users:
        text = 'Пользователи из БД:\n' + '\n'.join([f'ID: {u[0]}, Баланс: {u[1]}' for u in users])
    else:
        text = 'Нет пользователей в БД.'
    text += f"\n\nПользователи, писавшие боту:\n{tracked if tracked else 'Нет активных пользователей.'}"
    await message.answer(text)
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from db import init_db, get_balance, delete_user, set_balance
from utils import get_ton_usdt_rate

TOKEN = os.getenv("REDOCASE_BOT_TOKEN")
if not TOKEN:
    raise SystemExit("Set REDOCASE_BOT_TOKEN environment variable with your bot token.")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

ADMIN_ID = 8208248742  # Ваш Telegram user_id

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
    # Добавляем популярные валюты для отображения и конвертации
    for cur in popular_currencies:
        kb.add(types.InlineKeyboardButton(f"Курс {cur}", callback_data=f"course_{cur}"))
    return kb


# --- Админ-команды ---
banned_users = set()

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ...existing code...

@dp.callback_query_handler(lambda c: c.data == "admin_ban" and c.from_user.id == ADMIN_ID)
async def admin_ban_menu(call: types.CallbackQuery):
    import sqlite3
    conn = sqlite3.connect('users.db')
    cur = conn.execute('SELECT user_id FROM users')
    users = cur.fetchall()
    conn.close()
    kb = types.InlineKeyboardMarkup(row_width=2)
    for u in users:
        kb.add(types.InlineKeyboardButton(f"Забанить {u[0]}", callback_data=f"ban_user_{u[0]}"))
    await call.message.edit_text("Выберите пользователя для бана:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("ban_user_") and c.from_user.id == ADMIN_ID)
async def ban_user_action(call: types.CallbackQuery):
    uid = int(call.data.split('_')[-1])
    banned_users.add(uid)
    await call.message.edit_text(f"Пользователь {uid} забанен.", reply_markup=admin_menu_kb())

@dp.callback_query_handler(lambda c: c.data == "admin_unban" and c.from_user.id == ADMIN_ID)
async def admin_unban_menu(call: types.CallbackQuery):
    kb = types.InlineKeyboardMarkup(row_width=2)
    for uid in banned_users:
        kb.add(types.InlineKeyboardButton(f"Разбанить {uid}", callback_data=f"unban_user_{uid}"))
    await call.message.edit_text("Выберите пользователя для разбана:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("unban_user_") and c.from_user.id == ADMIN_ID)
async def unban_user_action(call: types.CallbackQuery):
    uid = int(call.data.split('_')[-1])
    banned_users.discard(uid)
    await call.message.edit_text(f"Пользователь {uid} разбанен.", reply_markup=admin_menu_kb())

@dp.callback_query_handler(lambda c: c.data == "admin_add_balance" and c.from_user.id == ADMIN_ID)
async def admin_balance_menu(call: types.CallbackQuery):
    import sqlite3
    conn = sqlite3.connect('users.db')
    cur = conn.execute('SELECT user_id FROM users')
    users = cur.fetchall()
    conn.close()
    kb = types.InlineKeyboardMarkup(row_width=2)
    for u in users:
        kb.add(types.InlineKeyboardButton(f"Баланс {u[0]}", callback_data=f"balance_user_{u[0]}"))
    await call.message.edit_text("Выберите пользователя для изменения баланса:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("balance_user_") and c.from_user.id == ADMIN_ID)
async def balance_user_action(call: types.CallbackQuery):
    uid = int(call.data.split('_')[-1])
    await call.message.edit_text(f"Введите новый баланс для пользователя {uid} (например: 10.5)")
    # Для полноценной работы нужен отдельный обработчик для ввода суммы

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

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text == "Пользователи")
async def users_cmd(message: types.Message):
    import sqlite3
    conn = sqlite3.connect('users.db')
    cur = conn.execute('SELECT user_id, balance FROM users')
    users = cur.fetchall()
    conn.close()
    tracked = '\n'.join([str(uid) for uid in active_users])
    if users:
        text = 'Пользователи из БД:\n' + '\n'.join([f'ID: {u[0]}, Баланс: {u[1]}' for u in users])
    else:
        text = 'Нет пользователей в БД.'
    text += f"\n\nПользователи, писавшие боту:\n{tracked if tracked else 'Нет активных пользователей.'}"
    await message.answer(text)
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from db import init_db, get_balance, delete_user, set_balance
from utils import get_ton_usdt_rate

TOKEN = os.getenv("REDOCASE_BOT_TOKEN")
if not TOKEN:
    raise SystemExit("Set REDOCASE_BOT_TOKEN environment variable with your bot token.")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

ADMIN_ID = 8208248742  # Ваш Telegram user_id

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


# --- Админ-команды ---
banned_users = set()

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton



@dp.callback_query_handler(lambda c: c.data == "admin_ban" and c.from_user.id == ADMIN_ID)
async def admin_ban_menu(call: types.CallbackQuery):
    import sqlite3
    conn = sqlite3.connect('users.db')
    cur = conn.execute('SELECT user_id FROM users')
    users = cur.fetchall()
    conn.close()
    kb = types.InlineKeyboardMarkup(row_width=2)
    for u in users:
        kb.add(types.InlineKeyboardButton(f"Забанить {u[0]}", callback_data=f"ban_user_{u[0]}"))
    await call.message.edit_text("Выберите пользователя для бана:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("ban_user_") and c.from_user.id == ADMIN_ID)
async def ban_user_action(call: types.CallbackQuery):
    uid = int(call.data.split('_')[-1])
    banned_users.add(uid)
    await call.message.edit_text(f"Пользователь {uid} забанен.", reply_markup=admin_menu_kb())

@dp.callback_query_handler(lambda c: c.data == "admin_unban" and c.from_user.id == ADMIN_ID)
async def admin_unban_menu(call: types.CallbackQuery):
    kb = types.InlineKeyboardMarkup(row_width=2)
    for uid in banned_users:
        kb.add(types.InlineKeyboardButton(f"Разбанить {uid}", callback_data=f"unban_user_{uid}"))
    await call.message.edit_text("Выберите пользователя для разбана:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("unban_user_") and c.from_user.id == ADMIN_ID)
async def unban_user_action(call: types.CallbackQuery):
    uid = int(call.data.split('_')[-1])
    banned_users.discard(uid)
    await call.message.edit_text(f"Пользователь {uid} разбанен.", reply_markup=admin_menu_kb())

@dp.callback_query_handler(lambda c: c.data == "admin_add_balance" and c.from_user.id == ADMIN_ID)
async def admin_balance_menu(call: types.CallbackQuery):
    import sqlite3
    conn = sqlite3.connect('users.db')
    cur = conn.execute('SELECT user_id FROM users')
    users = cur.fetchall()
    conn.close()
    kb = types.InlineKeyboardMarkup(row_width=2)
    for u in users:
        kb.add(types.InlineKeyboardButton(f"Баланс {u[0]}", callback_data=f"balance_user_{u[0]}"))
    await call.message.edit_text("Выберите пользователя для изменения баланса:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("balance_user_") and c.from_user.id == ADMIN_ID)
async def balance_user_action(call: types.CallbackQuery):
    uid = int(call.data.split('_')[-1])
    await call.message.edit_text(f"Введите новый баланс для пользователя {uid} (например: 10.5)")
    # Для полноценной работы нужен отдельный обработчик для ввода суммы

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

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text == "Пользователи")
async def users_cmd(message: types.Message):
    import sqlite3
    conn = sqlite3.connect('users.db')
    cur = conn.execute('SELECT user_id, balance FROM users')
    users = cur.fetchall()
    conn.close()
    tracked = '\n'.join([str(uid) for uid in active_users])
    if users:
        text = 'Пользователи из БД:\n' + '\n'.join([f'ID: {u[0]}, Баланс: {u[1]}' for u in users])
    else:
        text = 'Нет пользователей в БД.'
    text += f"\n\nПользователи, писавшие боту:\n{tracked if tracked else 'Нет активных пользователей.'}"
    await message.answer(text)

# Удаление старого сообщения (если есть)
async def safe_delete(msg):
    try:
        await msg.delete()
    except Exception:
        pass



@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    active_users.add(message.from_user.id)
    # Добавляем пользователя в БД, если его нет
    from db import set_balance, get_balance
    uid = message.from_user.id
    try:
        get_balance(uid)
        set_balance(uid, get_balance(uid))
    except Exception:
        set_balance(uid, 0.0)
    if message.from_user.id in banned_users:
        await message.answer("Вы забанены.")
        return
    if message.chat.type == "private":
        await message.answer(WELCOME_TEXT, reply_markup=main_menu_inline())
        # Убираем обычную клавиатуру, если она была
        await message.answer("", reply_markup=types.ReplyKeyboardRemove())


# Инлайн-обработчики
from db import get_history

# Для простоты: хранить язык в памяти (на практике — в БД)
user_lang = {}

@dp.callback_query_handler(lambda c: c.data in ["balance", "deposit", "course", "ref", "support", "logout", "mainmenu", "history", "langswitch"])
async def inline_menu_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    if user_id in banned_users:
        await call.message.edit_text("Вы забанены.")
        return
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
                "После перевода обязательно напишите в поддержку (@RedoBotSupport) и приложите скриншот или ссылку на транзакцию. "
                "Без подтверждения пополнение не будет зачислено!"
            )
        else:
            text = (
                f"To deposit, send TON to address:\n<code>{ton_addr}</code>\n\n"
                "After sending, be sure to contact support (@RedoBotSupport) and attach a screenshot or transaction link. "
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
    elif call.data.startswith("course_"):
        cur = call.data.split('_')[1]
        text = f"Курс {cur}: ... (реализовать API)"
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
    await call.answer()

# Команда /balance
@dp.message_handler(commands=["balance"])
async def balance_handler(message: types.Message):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    await message.answer(f"Ваш баланс: {balance:.4f} TON")


if __name__ == "__main__":
    init_db()
    executor.start_polling(dp, skip_updates=True)
