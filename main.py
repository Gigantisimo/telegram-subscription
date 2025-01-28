import os
import logging
from datetime import datetime, timedelta, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext,
    ConversationHandler,
    MessageHandler,
    Filters
)
from dotenv import load_dotenv
import matplotlib.pyplot as plt
from io import BytesIO
from database import Database

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования для Vercel (без файлов)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    # Убираем запись в файл, используем stdout
)
logger = logging.getLogger(__name__)

# Константы для ConversationHandler
NAME, COST, DATE = range(3)

# Конфигурация
TOKEN = os.getenv('TELEGRAM_TOKEN')
DB_FILE = ':memory:'  # Используем in-memory SQLite для Vercel

# Инициализация базы данных
db = Database(DB_FILE)

def main_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Добавить подписку", callback_data='add')],
        [InlineKeyboardButton("📋 Список подписок", callback_data='list')],
        [InlineKeyboardButton("📊 Статистика расходов", callback_data='stats')],
        [InlineKeyboardButton("❌ Удалить подписку", callback_data='delete')]
    ]
    return InlineKeyboardMarkup(keyboard)

def start(update: Update, context: CallbackContext) -> None:
    try:
        user = update.effective_user
        # Добавляем пользователя в БД
        db.add_user(user.id, user.username, user.first_name)
        
        logger.info(f"New user started bot: {user.id} ({user.username})")
        
        update.message.reply_text(
            f"Привет, {user.first_name}! Я помогу тебе управлять подписками.\n"
            "Выбери действие:",
            reply_markup=main_menu()
        )
    except Exception as e:
        logger.error(f"Error in start handler: {str(e)}", exc_info=True)
        update.message.reply_text("Произошла ошибка. Попробуйте позже.")

def add_subscription(update: Update, context: CallbackContext) -> int:
    try:
        query = update.callback_query
        query.answer()
        query.edit_message_text("Введите название подписки:")
        return NAME
    except Exception as e:
        logger.error(f"Error in add_subscription handler: {str(e)}", exc_info=True)
        query.edit_message_text("Произошла ошибка. Попробуйте позже.", reply_markup=main_menu())
        return ConversationHandler.END

def get_name(update: Update, context: CallbackContext) -> int:
    try:
        context.user_data['subscription'] = {'name': update.message.text}
        update.message.reply_text("Введите стоимость подписки (в формате 999.99):")
        return COST
    except Exception as e:
        logger.error(f"Error in get_name handler: {str(e)}", exc_info=True)
        update.message.reply_text("Произошла ошибка. Попробуйте позже.", reply_markup=main_menu())
        return ConversationHandler.END

def get_cost(update: Update, context: CallbackContext) -> int:
    try:
        cost = float(update.message.text)
        context.user_data['subscription']['cost'] = cost
        update.message.reply_text("Введите дату следующего платежа (ДД.ММ.ГГГГ):")
        return DATE
    except ValueError:
        update.message.reply_text("❌ Неверный формат стоимости. Попробуйте снова:")
        return COST
    except Exception as e:
        logger.error(f"Error in get_cost handler: {str(e)}", exc_info=True)
        update.message.reply_text("Произошла ошибка. Попробуйте позже.", reply_markup=main_menu())
        return ConversationHandler.END

def get_date(update: Update, context: CallbackContext) -> int:
    try:
        date_str = update.message.text
        payment_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        
        # Сохранение подписки в БД
        user_id = update.effective_user.id
        subscription = context.user_data['subscription']
        db.add_subscription(
            user_id,
            subscription['name'],
            subscription['cost'],
            payment_date.strftime("%Y-%m-%d")
        )
        
        logger.info(f"New subscription added by user {user_id}: {subscription['name']}")
        
        update.message.reply_text(
            "✅ Подписка успешно добавлена!", 
            reply_markup=main_menu()
        )
        return ConversationHandler.END
    except ValueError:
        update.message.reply_text("❌ Неверный формат даты. Попробуйте снова (ДД.ММ.ГГГГ):")
        return DATE
    except Exception as e:
        logger.error(f"Error in get_date handler: {str(e)}", exc_info=True)
        update.message.reply_text("Произошла ошибка. Попробуйте позже.", reply_markup=main_menu())
        return ConversationHandler.END

def list_subscriptions(update: Update, context: CallbackContext) -> None:
    try:
        query = update.callback_query
        query.answer()
        
        user_id = update.effective_user.id
        subscriptions = db.get_user_subscriptions(user_id)
        
        if not subscriptions:
            query.edit_message_text("Список подписок пуст.", reply_markup=main_menu())
            return
        
        response = "📋 Ваши подписки:\n\n"
        for sub in subscriptions:
            response += f"{sub['id']}. {sub['name']} - {sub['cost']} руб. (следующий платеж: {sub['payment_date']})\n"
        
        query.edit_message_text(response, reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Error in list_subscriptions handler: {str(e)}", exc_info=True)
        query.edit_message_text("Произошла ошибка. Попробуйте позже.", reply_markup=main_menu())

def show_stats(update: Update, context: CallbackContext) -> None:
    try:
        query = update.callback_query
        query.answer()
        
        user_id = update.effective_user.id
        subscriptions = db.get_user_subscriptions(user_id)
        
        if not subscriptions:
            query.edit_message_text("Нет данных для статистики.", reply_markup=main_menu())
            return
        
        # Создание графика
        plt.figure(figsize=(10, 5))
        names = [sub['name'] for sub in subscriptions]
        costs = [sub['cost'] for sub in subscriptions]
        
        plt.bar(names, costs)
        plt.title('Ежемесячные расходы на подписки')
        plt.ylabel('Рубли')
        plt.xticks(rotation=45)
        
        # Сохранение в буфер
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        # Отправка изображения
        context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=buf,
            caption="📊 Статистика ваших расходов:",
            reply_markup=main_menu()
        )
        buf.close()
    except Exception as e:
        logger.error(f"Error in show_stats handler: {str(e)}", exc_info=True)
        query.edit_message_text("Произошла ошибка при формировании статистики.", reply_markup=main_menu())

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Действие отменено.", reply_markup=main_menu())
    return ConversationHandler.END

def error_handler(update: Update, context: CallbackContext) -> None:
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)
    try:
        if update.effective_message:
            update.effective_message.reply_text(
                "Произошла ошибка при обработке запроса. Попробуйте позже.",
                reply_markup=main_menu()
            )
    except Exception as e:
        logger.error(f"Error in error handler: {str(e)}", exc_info=True)

def check_subscriptions_for_reminders(context: CallbackContext) -> None:
    """Проверка подписок и отправка напоминаний за день до оплаты."""
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    # Получаем всех пользователей из базы данных
    users = db.get_all_users()  # Вам нужно будет реализовать этот метод

    for user in users:
        user_id = user['user_id']
        subscriptions = db.get_user_subscriptions(user_id)

        for sub in subscriptions:
            payment_date = datetime.strptime(sub['payment_date'], "%Y-%m-%d").date()
            if payment_date == tomorrow:
                context.bot.send_message(
                    chat_id=user_id,
                    text=f"🔔 Напоминание: Ваша подписка '{sub['name']}' истекает завтра ({payment_date})."
                )

def delete_subscription(update: Update, context: CallbackContext) -> None:
    try:
        query = update.callback_query
        query.answer()
        
        user_id = update.effective_user.id
        subscriptions = db.get_user_subscriptions(user_id)
        
        if not subscriptions:
            query.edit_message_text("Список подписок пуст.", reply_markup=main_menu())
            return
        
        keyboard = []
        for sub in subscriptions:
            keyboard.append([InlineKeyboardButton(
                f"❌ {sub['name']} - {sub['cost']} руб.",
                callback_data=f"del_{sub['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='back')])
        
        query.edit_message_text(
            "Выберите подписку для удаления:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in delete_subscription handler: {str(e)}", exc_info=True)
        query.edit_message_text("Произошла ошибка. Попробуйте позже.", reply_markup=main_menu())

def handle_deletion(update: Update, context: CallbackContext) -> None:
    try:
        query = update.callback_query
        query.answer()
        
        if query.data == 'back':
            query.edit_message_text("Выберите действие:", reply_markup=main_menu())
            return
            
        sub_id = int(query.data.split('_')[1])
        user_id = update.effective_user.id
        
        if db.delete_subscription(sub_id, user_id):
            query.edit_message_text("✅ Подписка успешно удалена!", reply_markup=main_menu())
        else:
            query.edit_message_text("❌ Не удалось удалить подписку.", reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Error in handle_deletion handler: {str(e)}", exc_info=True)
        query.edit_message_text("Произошла ошибка. Попробуйте позже.", reply_markup=main_menu())

def main() -> None:
    try:
        updater = Updater(TOKEN)
        dp = updater.dispatcher

        # Запланируйте выполнение функции каждый день
        job_queue = updater.job_queue
        reminder_time = time(9, 0, 0)  # Используем time вместо datetime.time
        job_queue.run_daily(check_subscriptions_for_reminders, time=reminder_time)

        # Обработчики команд
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(add_subscription, pattern='^add$')],
            states={
                NAME: [MessageHandler(Filters.text & ~Filters.command, get_name)],
                COST: [MessageHandler(Filters.text & ~Filters.command, get_cost)],
                DATE: [MessageHandler(Filters.text & ~Filters.command, get_date)]
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )

        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(conv_handler)
        dp.add_handler(CallbackQueryHandler(list_subscriptions, pattern='^list$'))
        dp.add_handler(CallbackQueryHandler(show_stats, pattern='^stats$'))
        dp.add_handler(CallbackQueryHandler(delete_subscription, pattern='^delete$'))
        dp.add_handler(CallbackQueryHandler(handle_deletion, pattern='^(del_|back)'))
        
        # Добавляем обработчик ошибок
        dp.add_error_handler(error_handler)

        logger.info("Bot started")
        updater.start_polling()
        updater.idle()
    except Exception as e:
        logger.critical(f"Critical error in main: {str(e)}", exc_info=True)

if __name__ == '__main__':
    print("Starting bot...")
    logger.info("Starting bot initialization")
    main()
    print("Bot stopped")