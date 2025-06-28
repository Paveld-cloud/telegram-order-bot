import os
import json
import requests
import gspread
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ConversationHandler,
    filters,
)
from google.oauth2.service_account import Credentials

# Переменные
TOKEN = os.getenv("BOT_TOKEN")
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1CPRIxtXQ_2IMVsSesMoHYuBTmjnEWDC8R6mR4BAhvEk/edit"
SHEET_NAME = "Лист1"
ITEMS_PER_PAGE = 5
user_state = {}

# Conversation States
PRODUCT, QUANTITY, NAME, PHONE = range(4)

def load_catalog():
    creds_info = json.loads(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"))
    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SPREADSHEET_URL).worksheet(SHEET_NAME)
    data = sheet.col_values(1)
    return [row.strip() for row in data if row.strip()][1:]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_state[user_id] = 0
    catalog = load_catalog()
    page = catalog[:ITEMS_PER_PAGE]
    message = "\n".join([f"{i+1}. {item}" for i, item in enumerate(page)])
    await update.message.reply_text(
        f"🌹 Каталог роз (1–{ITEMS_PER_PAGE}):\n{message}\n\nНапиши название сорта или нажми /more"
    )
    return PRODUCT

async def more(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    catalog = load_catalog()
    current_page = user_state.get(user_id, 0) + 1
    start_index = current_page * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    page = catalog[start_index:end_index]
    if not page:
        await update.message.reply_text("📦 Это был конец списка.")
        return PRODUCT
    user_state[user_id] = current_page
    message = "\n".join([f"{i+1+start_index}. {item}" for i, item in enumerate(page)])
    await update.message.reply_text(
        f"🌹 Каталог (поз. {start_index+1}–{min(end_index, len(catalog))}):\n{message}\n\nНапиши название сорта или /more"
    )
    return PRODUCT

async def handle_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product = update.message.text.strip()
    catalog = load_catalog()
    if product not in catalog:
        await update.message.reply_text("❌ Такого сорта нет в каталоге. Попробуй снова.")
        return PRODUCT
    context.user_data["product"] = product
    await update.message.reply_text("Сколько штук?")
    return QUANTITY

async def handle_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        quantity = int(update.message.text.strip())
        context.user_data["quantity"] = quantity
    except:
        await update.message.reply_text("Введите число — сколько штук?")
        return QUANTITY
    await update.message.reply_text("Введите ваше имя:")
    return NAME

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Введите номер телефона:")
    return PHONE

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text.strip()
    product = context.user_data.get("product")
    quantity = context.user_data.get("quantity")
    name = context.user_data.get("name")
    phone = context.user_data.get("phone")
    total = 30000 * quantity
    commission = total * 0.10

    payload = {
        "product": product,
        "quantity": quantity,
        "name": name,
        "phone": phone,
        "total": total,
        "commission": commission
    }

    try:
        requests.post(MAKE_WEBHOOK_URL, json=payload)
    except Exception as e:
        print("Webhook error:", e)

    await update.message.reply_text(
        f"✅ Заказ оформлен!\nСорт: {product}\nКол-во: {quantity}\nСумма: {total} сум\nСкоро с вами свяжется менеджер."
    )
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PRODUCT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product),
                CommandHandler("more", more)
            ],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quantity)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()

