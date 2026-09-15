import os
import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
MY_USERNAME = os.environ.get("MY_USERNAME", "твой_username")
DATA_FILE = "bookings.json"
PORT = int(os.environ.get("PORT", 10000))
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

user_state = {}

def load_bookings():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_booking(booking):
    bookings = load_bookings()
    bookings.append(booking)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(bookings, f, ensure_ascii=False, indent=2)

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎤 Записаться на урок", callback_data="book")],
        [
            InlineKeyboardButton("💸 Оплата", callback_data="prices"),
            InlineKeyboardButton("👩‍🎓 Обо мне", callback_data="about"),
        ],
        [InlineKeyboardButton("📋 Мои записи", callback_data="my")],
    ])

async def show_menu(update, context):
    text = (
        "Привет! Я бот преподавателя вокала 🎤\n\n"
        "Здесь ты можешь узнать о занятиях и записаться на урок.\n"
        "Выбери, что тебя интересует:"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu())

async def menu_handler(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    is_admin = (user_id == ADMIN_ID)

    if data == "prices":
        text = (
            "💸 *Оплата*\n\n"
            "Я работаю по системе *Pay What You Want* "
            "(плати сколько хочешь).\n\n"
            "Ты сам выбираешь сумму за урок:\n"
            "— 100₽\n"
            "— 500₽\n"
            "— 1000₽\n"
            "— или любую другую\n\n"
            "Главное — чтобы тебе было комфортно 🎶\n\n"
            f"Способ оплаты: напиши мне @{MY_USERNAME}"
        )
        await query.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="menu")]]))

    elif data == "about":
        text = (
            "👩‍🎓 *Обо мне*\n\n"
            "Я преподаватель вокала. Работаю *онлайн* — "
            "из любой точки мира.\n\n"
            "Помогаю поставить голос, дыхание и уверенность. "
            "Работаю с начинающими и продолжающими."
        )
        await query.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="menu")]]))

    elif data == "book":
        text = (
            "🎤 *Записаться на урок*\n\n"
            "Я работаю по системе *Pay What You Want*.\n"
            "Это значит: ты сам определяешь стоимость урока.\n\n"
            "Хочешь — 100₽, хочешь — 2000₽. Сумма на твоё усмотрение.\n\n"
            "📌 Запись подтверждается только после оплаты."
        )
        buttons = [[InlineKeyboardButton("💳 Оплатить и записаться", callback_data="pay")]]
        if is_admin:
            buttons.append([InlineKeyboardButton("🔓 Записаться без оплаты", callback_data="book_free")])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu")])
        await query.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "pay":
        text = (
            "💳 *Оплата подключается*\n\n"
            "Скоро здесь будет кнопка оплаты.\n"
            f"Пока напиши мне напрямую: @{MY_USERNAME}\n\n"
            "После оплаты я открою запись на урок 🎤"
        )
        await query.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="book")]]))

    elif data == "book_free":
        if not is_admin:
            await query.edit_message_text("Нет доступа.")
            return
        user_state[user_id] = {"step": "name", "paid": True}
        await query.edit_message_text(
            "🔓 Админ-режим: запись без оплаты.\n\nКак зовут ученика?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="menu")]])
        )

    elif data == "my":
        bookings = load_bookings()
        my = [b for b in bookings if b["user_id"] == user_id]
        if not my:
            text = "У тебя пока нет записей 📭"
        else:
            text = "📋 *Твои записи:*\n\n"
            for b in my:
                mark = "✅" if b.get("paid") else "⏳"
                text += f"{mark} {b['name']} — {b['time']}\n"
        await query.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="menu")]]))

    elif data == "menu":
        await show_menu(update, context)

async def start(update, context):
    await show_menu(update, context)

async def handle_message(update, context):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id not in user_state:
        await update.message.reply_text("Нажми /start, чтобы начать 🎤")
        return

    step = user_state[user_id]["step"]

    if step == "name":
        user_state[user_id]["name"] = text
        user_state[user_id]["step"] = "time"
        await update.message.reply_text(
            f"Приятно познакомиться, {text}! 🎶\n\n"
            "Напиши удобный день и время (по Москве).\n"
            "Например: «Суббота, 15:00»"
        )

    elif step == "time":
        user_state[user_id]["time"] = text
        name = user_state[user_id]["name"]
        paid = user_state[user_id].get("paid", False)
        username = update.message.from_user.username or "—"

        save_booking({
            "user_id": user_id,
            "name": name,
            "time": text,
            "username": username,
            "paid": paid
        })

        await update.message.reply_text(
            f"Спасибо, {name}! ✅\n\n"
            f"Заявка на *{text}* принята.\n"
            f"Я свяжусь с тобой в ближайшее время 🎤",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

        tag = "🔓 БЕЗ ОПЛАТЫ (админ)" if paid else "💳 ждёт оплаты"
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"🎤 *Новая заявка!*\n\n"
                f"👤 Имя: {name}\n"
                f"🕐 Время: {text}\n"
                f"💬 Telegram: @{username}\n"
                f"📌 Статус: {tag}"
            ),
            parse_mode="Markdown"
        )

        del user_state[user_id]

async def admin(update, context):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Нет доступа.")
        return
    bookings = load_bookings()
    if not bookings:
        await update.message.reply_text("Пока нет заявок 📭")
        return
    text = f"📋 *Все заявки* ({len(bookings)}):\n\n"
    for i, b in enumerate(bookings, 1):
        mark = "✅" if b.get("paid") else "⏳"
        text += f"{i}. {mark} {b['name']} — {b['time']} (@{b['username']})\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def post_init(app: Application):
    if RENDER_URL:
        webhook_url = f"{RENDER_URL}/webhook"
        try:
            await app.bot.delete_webhook(drop_pending_updates=True)
            await asyncio.sleep(3)
            await app.bot.set_webhook(webhook_url)
            print(f"Вебхук установлен: {webhook_url}")
        except Exception as e:
            print(f"Ошибка вебхука: {e}")

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(menu_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен...")

    if RENDER_URL:
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"{RENDER_URL}/webhook",
            url_path="/webhook"
        )
    else:
        app.run_polling()

if __name__ == "__main__":
    main()
