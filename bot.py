
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler
import requests
import os

TOKEN = os.getenv("BOT_TOKEN")

PRODUCT, QUANTITY, NAME, PHONE = range(4)

catalog = {
    "Роза Аваланж": 50000,
    "Роза Анжелика": 50000,
    "Роза Паскаль": 50000
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[item] for item in catalog.keys()]
    await update.message.reply_text(
        "Выберите сорт розы:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return PRODUCT

async def select_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["product"] = update.message.text
    await update.message.reply_text("Сколько штук?")
    return QUANTITY

async def select_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["quantity"] = int(update.message.text)
    await update.message.reply_text("Введите ваше имя:")
    return NAME

async def enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Введите номер телефона:")
    return PHONE

async def enter_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text

    product = context.user_data.get("product")
    quantity = context.user_data.get("quantity")
    name = context.user_data.get("name")
    phone = context.user_data.get("phone")
    price = catalog.get(product, 0)
    total = price * quantity
    commission = total * 0.10

    webhook_url = os.getenv("MAKE_WEBHOOK_URL")
    payload = {
        "product": product,
        "quantity": quantity,
        "name": name,
        "phone": phone,
        "total": total,
        "commission": commission
    }

    try:
        requests.post(webhook_url, json=payload)
    except Exception as e:
        print(f"Ошибка при отправке webhook: {e}")

    await update.message.reply_text(
        f"Спасибо за заказ!\n"
        f"Товар: {product}\n"
        f"Кол-во: {quantity}\n"
        f"Итого: {total} сум\n"
        f"Скоро с вами свяжется менеджер."
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_product)],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_quantity)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
