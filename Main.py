import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")  # Replace with your token if not using Railway

FILE_DB = "file_db.json"

# Load DB
def load_db():
    if os.path.exists(FILE_DB):
        with open(FILE_DB, "r") as f:
            return json.load(f)
    return {}

# Save DB
def save_db(data):
    with open(FILE_DB, "w") as f:
        json.dump(data, f, indent=2)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a video and I will give you a private streaming/download link!")

# Handle video
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.video or update.message.document

    if not file:
        await update.message.reply_text("❌ Please send a valid video or file.")
        return

    file_id = file.file_id
    file_unique_id = file.file_unique_id

    db = load_db()
    db[file_unique_id] = file_id
    save_db(db)

    bot_username = (await context.bot.get_me()).username
    share_link = f"https://t.me/{bot_username}?start={file_unique_id}"

    await update.message.reply_text(f"✅ Your file has been saved!\n🔗 Link: {share_link}")

# Start via shared link
async def start_with_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        file_uid = context.args[0]
        db = load_db()
        file_id = db.get(file_uid)

        if file_id:
            await update.message.reply_video(file_id)
        else:
            await update.message.reply_text("❌ File not found or expired.")
    else:
        await start(update, context)

# Main
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_with_file))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    app.run_polling()

if __name__ == "__main__":
    main()
