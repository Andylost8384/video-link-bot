import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

DATA_FILE = "file_db.json"

# Load existing database or create new
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        file_db = json.load(f)
else:
    file_db = {}

# Save to JSON file
def save_file_db():
    with open(DATA_FILE, "w") as f:
        json.dump(file_db, f, indent=2)

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Send me a video and I'll give you a download link.")

# Handle video uploads
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.video or update.message.document
    if not file:
        await update.message.reply_text("❌ Please send a valid video or file.")
        return

    file_id = file.file_id
    unique_id = file.file_unique_id
    file_db[unique_id] = file_id
    save_file_db()

    bot_username = (await context.bot.get_me()).username
    share_link = f"https://t.me/{bot_username}?start=FILE_{unique_id}"

    await update.message.reply_text(
        f"✅ Your File Stored!\n🔗 Link: {share_link}"
    )

# Handle /start FILE_xxx links
async def handle_start_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args and args[0].startswith("FILE_"):
        unique_id = args[0][5:]
        file_id = file_db.get(unique_id)

        if file_id:
            await update.message.reply_video(file_id)
        else:
            await update.message.reply_text("❌ File not found or expired.")
    else:
        await start(update, context)

# Main function
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", handle_start_file))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))

    print("🤖 Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
