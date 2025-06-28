import os
import requests
import gspread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# Авторизация в Google Sheets
from google.oauth2.service_account import Credentials

# Переменные
TOKEN = os.getenv("BOT_TOKEN")
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1CPRIxtXQ_2IMVsSesMoHYuBTmjnEWDC8R6mR4BAhvEk/edit"
SHEET_NAME = "Лист1"

# Настройки
ITEMS_PER_PAGE = 5
user_state = {}

# Подключение к Google Таблице
def load_catalog():
    creds = Credentials.from_service_account_file("credentials.json", scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SPREADSHEET_URL).worksheet(SHEET_NAME)
    data = sheet.col_values(1)
    return [row.strip() for row in data if row.strip()][1:]  # Пропускаем заголовок

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_state[user_id] = 0  # первая страница
    catalog = load_catalog()
    page = catalog[:ITEMS_PER_PAGE]
    message = "\n".join([f"{i+1}. {item}" for i, item in enumerate(page)])
    await update.message.reply_text(f"🌹 Каталог роз (1–{ITEMS_PER_PAGE}):\n{message}\n\nНапиши название сорта или нажми /ещё")

async def more(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    catalog = load_catalog()
    current_page = user_state.get(user_id, 0) + 1
    start_index = current_page * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    page = catalog[start_index:end_index]
    if not page:
        await update.message.reply_text("📦 Это был конец списка.")
        return
    user_state[user_id] = current_page
    message = "\n".join([f"{i+1+start_index}. {item}" for i, item in enumerate(page)])
    await update.message.reply_text(f"🌹 Каталог (поз. {start_index+1}–{min(end_index, len(catalog))}):\n{message}\n\nНапиши название сорта или /ещё")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product = update.message.text.strip()
    catalog = load_catalog()
    if product not in catalog:
        await update.message.reply_text("❌ Такого сорта нет в каталоге. Попробуй снова.")
        return
    context.user_data["product"] = product
    await update.message.reply_text("Сколько штук?")
    return

async def handle_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        quantity = int(update.message.text.strip())
        context.user_data["quantity"] = quantity
    except:
        await update.message.reply_text("Введите число — сколько штук?")
        return
    await update.message.reply_text("Введите ваше имя:")

    return

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Введите номер телефона:")

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

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ещё", more))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()