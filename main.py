import os
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from supabase import create_client, Client

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")  # Replace if not using Railway

# Supabase credentials (recommended: store in Railway secrets)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project-id.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-service-role-key")

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a video and I will give you a private streaming/download link!")

# Save file to Supabase
def save_file_to_supabase(file_unique_id, file_id):
    data = {
        "file_unique_id": file_unique_id,
        "file_id": file_id,
        "created_at": datetime.utcnow().isoformat()
    }
    supabase.table("files").insert(data).execute()

# Get file_id from Supabase using unique_id
def get_file_id_from_supabase(file_unique_id):
    result = supabase.table("files").select("file_id").eq("file_unique_id", file_unique_id).execute()
    if result.data and len(result.data) > 0:
        return result.data[0]["file_id"]
    return None

# Handle video upload
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.video or update.message.document

    if not file:
        await update.message.reply_text("❌ Please send a valid video or file.")
        return

    file_id = file.file_id
    file_unique_id = file.file_unique_id

    # Save to Supabase
    save_file_to_supabase(file_unique_id, file_id)

    bot_username = (await context.bot.get_me()).username
    share_link = f"https://t.me/{bot_username}?start={file_unique_id}"

    await update.message.reply_text(f"✅ Your file has been saved!\n🔗 Link: {share_link}")

# Handle shared link
async def start_with_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        file_uid = context.args[0]
        file_id = get_file_id_from_supabase(file_uid)

        if file_id:
            await update.message.reply_video(file_id)
        else:
            await update.message.reply_text("❌ File not found or expired.")
    else:
        await start(update, context)

# Main function
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_with_file))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    app.run_polling()

if __name__ == "__main__":
    main()
