import sqlite3
from contextlib import closing

DB_PATH = 'users.db'

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    balance REAL DEFAULT 0.0,
                    ref_code TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT,
                    amount REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

def get_balance(user_id):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute('SELECT balance FROM users WHERE user_id=?', (user_id,))
        row = cur.fetchone()
        return row[0] if row else 0.0

def set_balance(user_id, amount):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute('INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, ?)', (user_id, amount))
            conn.execute('UPDATE users SET balance=? WHERE user_id=?', (amount, user_id))

def delete_user(user_id):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute('DELETE FROM users WHERE user_id=?', (user_id,))
            conn.execute('DELETE FROM history WHERE user_id=?', (user_id,))

def add_history(user_id, action, amount):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute('INSERT INTO history (user_id, action, amount) VALUES (?, ?, ?)', (user_id, action, amount))

def get_history(user_id, limit=10):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute('SELECT action, amount, timestamp FROM history WHERE user_id=? ORDER BY timestamp DESC LIMIT ?', (user_id, limit))
        return cur.fetchall()
