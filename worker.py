import os
import json
import asyncio
import httpx
import redis.asyncio as redis
from dotenv import load_dotenv

from processors import process_voice, process_image, process_url
from models import NormalizedEntry
from datetime import datetime
from storage import save_to_github, get_from_github
from agent import analyze_knowledge, answer_question_with_context

from database import init_db, save_message, get_chat_history

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
r = redis.from_url(REDIS_URL, decode_responses=True)

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def send_telegram_message(chat_id: int, text: str):
    """Permite al Worker enviar mensajes de vuelta al usuario en Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)

async def get_telegram_file_url(file_id: str) -> str:
    """Usa el API de Telegram para convertir un file_id en una URL de descarga real."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        file_path = response.json()["result"]["file_path"]
        return f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"

async def process_job(job_data: dict):
    """El núcleo del Worker: toma el pedido y usa los procesadores de la Fase 2."""
    user_id = job_data['user_id']
    chat_id = job_data['chat_id']
    msg_type = job_data['type']
    text = job_data.get('text')
    file_id = job_data.get('file_id')
    
    entry = NormalizedEntry(source_type=msg_type, timestamp=datetime.utcnow())

    print(f"\n[Usuario {user_id}] Procesando contenido tipo: {msg_type}")
    await send_telegram_message(chat_id, "El Worker ha iniciado el análisis...")

    try:
        # 1. ES TEXTO O URL
        if msg_type == "text" and text:
            if "http" in text:
                print("🔗 Detectado enlace. Raspando artículo...")
                entry.source_type = "url"
                entry.url = text
                entry.extracted_text = await process_url(text)
            else:
                entry.original_text = text

        # 2. ES MULTIMEDIA (Voz o Imagen)
        elif msg_type == "media" and file_id:
            file_url = await get_telegram_file_url(file_id)
            
            if job_data.get('is_voice'):
                print("🎙️ Descargando audio de Telegram y transcribiendo con Whisper...")
                entry.source_type = "voice"
                async with httpx.AsyncClient() as client:
                    audio_response = await client.get(file_url)
                entry.transcription = await process_voice(audio_response.content)
                
            else:
                print("🖼️ Pasando imagen a GPT-4 Vision...")
                entry.source_type = "image"
                entry.original_text = job_data.get('caption')
                entry.image_description = await process_image(file_url)

        print("✅ Procesamiento multimedia terminado.")
        print("🧠 Enviando al Agente de IA para clasificación...")

        metadata = await analyze_knowledge(entry.core_content)

        await save_message(user_id, "user", entry.core_content)

        historial = await get_chat_history(user_id, limit=5)

        metadata = await analyze_knowledge(entry.core_content, chat_history=historial)

        print(f"📊 Análisis del Agente:")
        print(f"   - Acción: {metadata.action}")
        print(f"   - Tema: {metadata.topic}")
        print(f"   - Etiquetas: {metadata.tags}")
        print(f"   - Resumen: {metadata.summary}")
        
        # --- Lógica de respuesta en Telegram ---
        respuesta_final = ""
        if metadata.action == 'discard':
            respuesta_final = "*Contenido descartado:* No parece ser útil para la base de conocimientos."
            
        elif metadata.action == 'ask_user':
            print(f"🔍 Buscando notas en GitHub sobre el tema: {metadata.topic}...")
            
            conocimiento_guardado = get_from_github(metadata.topic)
            
            if conocimiento_guardado:
                respuesta_final = await answer_question_with_context(
                    question=entry.core_content,
                    knowledge_context=conocimiento_guardado
                )
            else:
                respuesta_final = f"Me preguntas sobre '{metadata.topic}', pero aún no tienes notas guardadas sobre este tema en tu Segundo Cerebro. ¿Quieres que guarde algo al respecto?"
            
        elif metadata.action == 'save':
            try:
                save_to_github(
                    topic=metadata.topic,
                    tags=metadata.tags,
                    summary=metadata.summary,
                    original_content=entry.core_content,
                    source_type=entry.source_type
                )
                respuesta_final = (
                    f"**¡Guardado en GitHub!**\n"
                    f"*Archivo:* `{metadata.topic}.md`\n"
                    f"*Etiquetas:* {', '.join(metadata.tags)}\n\n"
                    f"*Resumen:*\n{metadata.summary}"
                )
            except Exception as e:
                respuesta_final = f"❌ Error al guardar en GitHub: {str(e)}"
        
        # Enviamos la respuesta a Telegram
        await send_telegram_message(chat_id, respuesta_final)
        
        # --- NUEVO: Guardamos la respuesta del bot en la memoria ---
        await save_message(user_id, "assistant", respuesta_final)

    except Exception as e:
        error_msg = f"❌ Error procesando tarea de {user_id}: {str(e)}"
        print(error_msg)
        await send_telegram_message(chat_id, error_msg)

async def run_worker():
    
    await init_db()
    
    print("Worker asíncrono encendido. Conectado a Redis. Esperando tareas...")
    while True:
        lista, job_json = await r.blpop("bot_queue")
        job_data = json.loads(job_json)
        await process_job(job_data)

if __name__ == "__main__":
    asyncio.run(run_worker())