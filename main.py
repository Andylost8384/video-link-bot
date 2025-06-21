import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from supabase import create_client, Client

# ENV variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://xyzcompany.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-secret-key")

# Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

    # Save to Supabase table
    try:
        supabase.table("files").insert({
            "file_id": file_id,
            "file_unique_id": file_unique_id
        }).execute()

        bot_username = (await context.bot.get_me()).username
        share_link = f"https://t.me/{bot_username}?start={file_unique_id}"
        await update.message.reply_text(f"✅ Your file has been saved!\n🔗 Link: {share_link}")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error saving to database: {e}")

# Start via link
async def start_with_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        file_uid = context.args[0]

        try:
            result = supabase.table("files").select("file_id").eq("file_unique_id", file_uid).single().execute()
            file_id = result.data['file_id']
            await update.message.reply_video(file_id)

        except Exception:
            await update.message.reply_text("❌ File not found or expired.")
    else:
        await start(update, context)

# Main entry point
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_with_file))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    app.run_polling()

if __name__ == "__main__":
    main()
