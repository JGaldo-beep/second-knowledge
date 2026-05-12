import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import json

# IMPORTANTE: Usamos la versión asíncrona de Redis
import redis.asyncio as redis

# Cargamos variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
r = redis.from_url(REDIS_URL, decode_responses=True)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ptb_app = Application.builder().token(TOKEN).build()

async def start(update: Update, context):
    """Send a message when the command /start is issued."""
    await update.message.reply_text("Hello! I am your AI Knowledge Base Bot. Send me text, links, or media!")

async def handle_message(update: Update, context):
    message = update.message
    user_id = message.from_user.id
    
    # 1. Creamos el paquete. Añadimos is_voice para ayudar al Worker
    job_data = {
        "user_id": user_id,
        "chat_id": message.chat_id,
        "message_id": message.message_id,
        "type": "text" if message.text else "media",
        "file_id": message.voice.file_id if message.voice else (message.photo[-1].file_id if message.photo else None),
        "text": message.text,
        "caption": message.caption,
        "is_voice": True if message.voice else False
    }

    # 2. Empujamos el trabajo a la cola asíncronamente (nota el 'await')
    await r.rpush("bot_queue", json.dumps(job_data))
    
    await message.reply_text("📥 Mensaje encolado. Mi worker ya lo está procesando...")
    
# Update your handlers
ptb_app.add_handler(CommandHandler("start", start))
# This handler catches text, voice, and photos
ptb_app.add_handler(MessageHandler(filters.TEXT | filters.VOICE | filters.PHOTO, handle_message))

# --- FastAPI Setup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI to handle PTB initialization."""
    await ptb_app.initialize()
    await ptb_app.start()
    
    await ptb_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    logger.info(f"Webhook set to {WEBHOOK_URL}/webhook")
    
    yield
    
    await ptb_app.stop()
    await ptb_app.shutdown()
    await r.aclose() # Cerramos la conexión de Redis limpiamente

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """The endpoint that Telegram sends updates to."""
    data = await request.json()
    update = Update.de_json(data, ptb_app.bot)
    
    await ptb_app.process_update(update)
    return {"status": "ok"}

@app.get("/")
def health_check():
    return {"status": "Bot server is running"}