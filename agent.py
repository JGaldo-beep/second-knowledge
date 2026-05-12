import os
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 1. Definimos la estructura exacta que queremos que el LLM nos devuelva
class KnowledgeMetadata(BaseModel):
    topic: str = Field(
        description="El tema principal o nombre de la carpeta (ej. 'IA_Agentes', 'Desarrollo_Nextjs', 'Linux', 'Estilo_Vida'). Usa CamelCase o guiones bajos, sin espacios."
    )
    tags: list[str] = Field(
        description="Una lista de 3 a 5 etiquetas ultra específicas sobre el contenido."
    )
    summary: str = Field(
        description="Un resumen conciso en formato Markdown, máximo 3 líneas. Destaca lo más importante."
    )
    action: str = Field(
        description="¿Qué debemos hacer con esto? Opciones: 'save' (es útil para la base de conocimientos), 'discard' (es basura o spam), 'ask_user' (si es un comando o pregunta directa)."
    )

async def analyze_knowledge(core_content: str, chat_history: list = None) -> KnowledgeMetadata:
    """Envía el contenido al LLM con su contexto histórico y fuerza una respuesta estructurada."""
    
    prompt_sistema = """
    Eres el Agente Orquestador de un sistema de "Segundo Cerebro" (Knowledge Base).
    Tu objetivo es analizar el contenido que el usuario ha guardado y clasificarlo meticulosamente.
    IMPORTANTE: Ten en cuenta el historial de conversación para entender el contexto.
    Si el usuario está respondiendo a una pregunta tuya, usa ese contexto para clasificar mejor.
    """

    messages = [{"role": "system", "content": prompt_sistema}]
    
    if chat_history:
        messages.extend(chat_history)
        
    messages.append({"role": "user", "content": f"Analiza el siguiente contenido:\n\n{core_content}"})

    completion = await client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=messages,
        response_format=KnowledgeMetadata,
        temperature=0.2
    )
    
    return completion.choices[0].message.parsed