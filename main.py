import os
import json
from datetime import datetime
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# ENV variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://bpljpoguhubrrkxkfccs.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-service-role-key")  # Service Role key recommended

bucket_name = "videos"  # Apna bucket name daalo
table_name = "files"    # Apna table name daalo

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a video and I will give you a private streaming/download link!")

# Helper function: Upload file bytes to Supabase Storage
async def upload_file_to_supabase(file_bytes: bytes, remote_path: str):
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket_name}/{remote_path}"
    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers=headers, content=file_bytes)
    return res

# Helper function: Insert metadata into Supabase table
async def insert_metadata_to_supabase(file_unique_id: str, file_id: str):
    url = f"{SUPABASE_URL}/rest/v1/{table_name}"
    insert_headers = {
        **headers,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    json_data = {
        "id": file_unique_id,          # assuming your table's primary key is 'id'
        "file_id": file_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers=insert_headers, json=json_data)
    return res

# Handle video or document video
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.video or update.message.document
    if not file:
        await update.message.reply_text("❌ Please send a valid video or file.")
        return

    file_id = file.file_id
    file_unique_id = file.file_unique_id
    print(f"Received file_id: {file_id}, unique_id: {file_unique_id}")

    file_obj = await context.bot.get_file(file_id)
    file_bytes = await file_obj.download_as_bytearray()
    print(f"Downloaded {len(file_bytes)} bytes")

    remote_path = f"{file_unique_id}.mp4"

    # Upload to Supabase Storage
    res_upload = supabase.storage.from_("videos").upload(remote_path, file_bytes, {"content-type": "video/mp4", "upsert": True})
    print(f"Upload response: {res_upload}")

    # Insert metadata to table
    res_insert = supabase.table("files").insert({
        "file_id": file_id,
        "file_unique_id": file_unique_id
    }).execute()
    print(f"Insert response: {res_insert}")

    bot_username = (await context.bot.get_me()).username
    share_link = f"https://t.me/{bot_username}?start={file_unique_id}"
    await update.message.reply_text(f"✅ Your file has been saved!\n🔗 Link: {share_link}")


    # Download file bytes from Telegram
    file_obj = await context.bot.get_file(file_id)
    file_bytes = await file_obj.download_as_bytearray()

    # Prepare remote path (you can organize as you want)
    remote_path = f"{file_unique_id}.mp4"  # Or any extension depending on your file

    # Upload file to Supabase Storage
    res_upload = await upload_file_to_supabase(file_bytes, remote_path)
    if res_upload.status_code not in (200, 201):
        await update.message.reply_text(f"❌ Upload failed: {res_upload.text}")
        return

    # Insert metadata to Supabase Table
    res_insert = await insert_metadata_to_supabase(file_unique_id, file_id)
    if res_insert.status_code not in (200, 201):
        await update.message.reply_text(f"⚠️ Metadata insert failed: {res_insert.text}")
        return

    bot_username = (await context.bot.get_me()).username
    share_link = f"https://t.me/{bot_username}?start={file_unique_id}"
    await update.message.reply_text(f"✅ Your file has been saved!\n🔗 Link: {share_link}")

# Start via link
async def start_with_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        file_uid = context.args[0]

        # Query Supabase table for file_id by unique id
        url = f"{SUPABASE_URL}/rest/v1/{table_name}?id=eq.{file_uid}"
        query_headers = {
            **headers,
            "Accept": "application/json",
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
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

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_with_file))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    app.run_polling()

if __name__ == "__main__":
    main()
