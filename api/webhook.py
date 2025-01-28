from flask import Flask, request, jsonify
import telebot
import os
from datetime import datetime, timedelta
import sys
import logging
from pathlib import Path

# Добавляем родительскую директорию в путь для импорта
sys.path.append(str(Path(__file__).parent.parent))

from main import (
    start, add_subscription, get_name, get_cost, get_date,
    list_subscriptions, show_stats, delete_subscription,
    handle_deletion, check_subscriptions_for_reminders
)
from database import Database

app = Flask(__name__)
bot = telebot.TeleBot(os.getenv('TELEGRAM_TOKEN'))
db = Database(':memory:')  # Используем in-memory SQLite

@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "Bot is running"})

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return jsonify({"status": "OK"}), 200
    return jsonify({"status": "Error"}), 403

# Регистрируем обработчики
@bot.message_handler(commands=['start'])
def handle_start(message):
    start(message, bot)

# Добавьте остальные обработчики по аналогии

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080))) 