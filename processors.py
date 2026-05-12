import os
import tempfile
import httpx
import trafilatura
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def process_voice(file_bytes: bytes) -> str:
    """Transcribe voice notes using Whisper."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
        temp_audio.write(file_bytes)
        temp_audio_path = temp_audio.name

    try:
        with open(temp_audio_path, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        return transcript.text
    finally:
        os.remove(temp_audio_path)

async def process_image(image_url: str) -> str:
    """Describe an image using GPT-4 Vision."""
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image in detail. Extract any readable text."},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
        max_tokens=500,
    )
    return response.choices[0].message.content

async def process_url(url: str) -> str:
    """Scrape and extract main text from a URL."""
    async with httpx.AsyncClient() as http_client:
        response = await http_client.get(url, follow_redirects=True)
    
    extracted = trafilatura.extract(response.text)
    return extracted if extracted else "Could not extract text from URL."