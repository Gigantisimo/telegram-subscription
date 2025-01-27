import sqlite3
from datetime import datetime
import logging
from typing import Dict, List, Optional

class Database:
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.init_db()

    def init_db(self):
        """Инициализация базы данных"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица подписок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT NOT NULL,
                    cost REAL NOT NULL,
                    payment_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            conn.commit()

    def add_user(self, user_id: int, username: str, first_name: str) -> None:
        """Добавление нового пользователя"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
            ''', (user_id, username, first_name))
            conn.commit()

    def add_subscription(self, user_id: int, name: str, cost: float, payment_date: str) -> int:
        """Добавление новой подписки"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO subscriptions (user_id, name, cost, payment_date)
                VALUES (?, ?, ?, ?)
            ''', (user_id, name, cost, payment_date))
            conn.commit()
            return cursor.lastrowid

    def get_user_subscriptions(self, user_id: int) -> List[Dict]:
        """Получение всех подписок пользователя"""
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM subscriptions 
                WHERE user_id = ? 
                ORDER BY payment_date
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]

    def delete_subscription(self, subscription_id: int, user_id: int) -> bool:
        """Удаление подписки"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM subscriptions 
                WHERE id = ? AND user_id = ?
            ''', (subscription_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_users(self) -> List[Dict]:
        """Получение всех пользователей."""
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users')
            return [dict(row) for row in cursor.fetchall()] 