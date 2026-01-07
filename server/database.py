import sqlite3
import bcrypt
import os

class Database:
    def __init__(self, db_name="game_server.db"):
        self.db_name = db_name
        self._init_db()

    def _get_connection(self):
        # Вмикаємо row_factory, щоб отримувати результати як словники
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Створює таблиці, якщо вони не існують."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    wins INTEGER DEFAULT 0,
                    games_played INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def register_user(self, username, password):
        """Хешує пароль і зберігає нового користувача."""
        if not username or not password:
            return False, "Нікнейм та пароль не можуть бути порожніми"

        # Хешування пароля
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)

        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, hashed)
                )
                conn.commit()
            return True, "Реєстрація успішна"
        except sqlite3.IntegrityError:
            return False, "Користувач з таким іменем вже існує"

    def authenticate_user(self, username, password):
        """Перевіряє пароль користувача."""
        with self._get_connection() as conn:
            user = conn.execute(
                "SELECT password_hash FROM users WHERE username = ?", 
                (username,)
            ).fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
            return True, "Авторизація успішна"
        return False, "Невірне ім'я користувача або пароль"

    def get_user_stats(self, username):
        """Отримує статистику гравця."""
        with self._get_connection() as conn:
            return conn.execute(
                "SELECT username, wins, games_played FROM users WHERE username = ?", 
                (username,)
            ).fetchone()