import os
from datetime import datetime
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# ✅ Static Configs
BOT_TOKEN = "7188831975:AAH3lwvnnlwQQDeTWvVGmebqR5Oos7EmP9U"
SUPABASE_URL = "https://bpljpoguhubrrkxkfccs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJwbGpwb2d1aHVicnJreGtmY2NzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTA0OTkyODgsImV4cCI6MjA2NjA3NTI4OH0.R2HPhC4ivM7lCQ3cwP52IW6EaXzN-xtaDW_OzjaV8qE"

bucket_name = "videos"
table_name = "files"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

# 🟢 Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a video and I will give you a private streaming/download link!")

# 📤 Upload video to Supabase Storage
async def upload_file_to_supabase(file_bytes: bytes, remote_path: str):
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket_name}/{remote_path}"
    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers=headers, content=file_bytes)
    return res

# 🗂️ Save metadata to Supabase Table
async def insert_metadata_to_supabase(file_unique_id: str, file_id: str):
    url = f"{SUPABASE_URL}/rest/v1/{table_name}"
    insert_headers = {
        **headers,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    json_data = {
        "id": file_unique_id,
        "file_id": file_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers=insert_headers, json=json_data)
    return res

# 📩 Handle file uploads from user
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.video or update.message.document
    if not file:
        await update.message.reply_text("❌ Please send a valid video or file.")
        return

    file_id = file.file_id
    file_unique_id = file.file_unique_id
    print("[DEBUG] file_id:", file_id, "file_unique_id:", file_unique_id)

    file_obj = await context.bot.get_file(file_id)
    file_bytes = await file_obj.download_as_bytearray()
    print("[DEBUG] downloaded bytes length:", len(file_bytes))

    remote_path = f"{file_unique_id}.mp4"
    res_upload = await upload_file_to_supabase(file_bytes, remote_path)
    print("[DEBUG] upload status:", res_upload.status_code, res_upload.text)

    if res_upload.status_code not in (200, 201):
        await update.message.reply_text(f"❌ Upload failed: {res_upload.text}")
        return

    res_insert = await insert_metadata_to_supabase(file_unique_id, file_id)
    print("[DEBUG] insert status:", res_insert.status_code, res_insert.text)

    if res_insert.status_code not in (200, 201):
        await update.message.reply_text(f"⚠️ Metadata insert failed: {res_insert.text}")
        return

    bot_username = (await context.bot.get_me()).username
    share_link = f"https://t.me/{bot_username}?start={file_unique_id}"
    await update.message.reply_text(f"✅ File saved!\n🔗 Your private link:\n{share_link}")


# 🔗 Handle /start?file_id link
async def start_with_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        file_uid = context.args[0]
        url = f"{SUPABASE_URL}/rest/v1/{table_name}?id=eq.{file_uid}"
        query_headers = {
            **headers,
            "Accept": "application/json"
        }
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=query_headers)

        if res.status_code == 200 and res.json():
            file_id = res.json()[0].get("file_id")
            await update.message.reply_video(file_id)
        else:
            await update.message.reply_text("❌ File not found or expired.")
    else:
        await start(update, context)

# 🚀 Launch bot
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_with_file))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    app.run_polling()

if __name__ == "__main__":
    main()
