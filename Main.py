import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

# Load or create database
DB_FILE = "file_db.json"
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({}, f)

def load_db():
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        file_id = args[0]
        db = load_db()
        if file_id in db:
            await update.message.reply_document(document=db[file_id])
        else:
            await update.message.reply_text("File not found.")
    else:
        await update.message.reply_text("Send a video to get a shareable link.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        db = load_db()
        db[file_id] = file_id
        save_db(db)
        bot_username = (await context.bot.get_me()).username
        share_link = f"https://t.me/{bot_username}?start={file_id}"
        await update.message.reply_text(f"✅ Your File Stored!")

await update.message.reply_text(f"✅ Your File Stored!\n🔗 Link: {share_link}")

app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.VIDEO, handle_video))

app.run_polling()
