import os
from fastapi import FastAPI, Request, Response
from telegram import Update, Bot
from telegram.ext import Application, ContextTypes
from telegram.ext import CommandHandler, MessageHandler, filters
import asyncio
import httpx
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://bpljpoguhubrrkxkfccs.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-service-role-key")
bucket_name = "videos"
table_name = "files"

app = FastAPI()
bot = Bot(token=BOT_TOKEN)
application = Application.builder().bot(bot).build()

# Supabase headers for REST calls
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

async def upload_file_to_supabase(file_bytes: bytes, remote_path: str):
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket_name}/{remote_path}"
    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers=headers, content=file_bytes)
    return res

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

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a video and I will give you a private streaming/download link!")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.video or update.message.document
    if not file:
        await update.message.reply_text("❌ Please send a valid video or file.")
        return

    file_id = file.file_id
    file_unique_id = file.file_unique_id

    file_obj = await context.bot.get_file(file_id)
    file_bytes = await file_obj.download_as_bytearray()

    remote_path = f"{file_unique_id}.mp4"

    # Upload to Supabase Storage
    res_upload = await upload_file_to_supabase(file_bytes, remote_path)
    if res_upload.status_code not in (200, 201):
        await update.message.reply_text(f"❌ Upload failed: {res_upload.text}")
        return

    # Insert metadata
    res_insert = await insert_metadata_to_supabase(file_unique_id, file_id)
    if res_insert.status_code not in (200, 201):
        await update.message.reply_text(f"⚠️ Metadata insert failed: {res_insert.text}")
        return

    bot_username = (await context.bot.get_me()).username
    share_link = f"https://t.me/{bot_username}?start={file_unique_id}"
    await update.message.reply_text(f"✅ Your file has been saved!\n🔗 Link: {share_link}")

async def start_with_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        file_uid = context.args[0]
        url = f"{SUPABASE_URL}/rest/v1/{table_name}?id=eq.{file_uid}"
        query_headers = {
            **headers,
            "Accept": "application/json",
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

# Register handlers to application
application.add_handler(CommandHandler("start", start_with_file))
application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))

@app.post(f"/webhook/{BOT_TOKEN}")
async def telegram_webhook(req: Request):
    json_update = await req.json()
    update = Update.de_json(json_update, bot)
    await application.process_update(update)
    return Response(status_code=200)

@app.on_event("startup")
async def on_startup():
    webhook_url = f"https://YOUR_PUBLIC_URL/webhook/{BOT_TOKEN}"  # <-- Replace with your public HTTPS URL from Railway
    await bot.set_webhook(webhook_url)

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
