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

async def analyze_knowledge(core_content: str, chat_history: list = None, available_topics: list = None) -> KnowledgeMetadata:
    """Envía el contenido al LLM con su contexto histórico y fuerza una respuesta estructurada."""
    
    temas_str = ", ".join(available_topics) if available_topics else "Ninguno todavía"
    
    prompt_sistema = f"""
    Eres el Agente Orquestador de un sistema de "Segundo Cerebro" (Knowledge Base).
    Tu objetivo es analizar el contenido que el usuario ha guardado y clasificarlo meticulosamente.
    IMPORTANTE: Ten en cuenta el historial de conversación para entender el contexto.
    
    ARCHIVOS/TEMAS EXISTENTES EN TU CEREBRO DIGITAL: [{temas_str}]
    
    REGLAS ESTRICTAS PARA EL TOPIC:
    - Si el usuario te hace una pregunta o pide buscar algo ('ask_user'), DEBES usar EXACTAMENTE uno de los temas de la lista de arriba que más se relacione. NO inventes temas nuevos al buscar.
    - Si el usuario envía información nueva ('save'), puedes usar un tema existente o inventar uno nuevo si el contenido no encaja en los actuales.
    
    REGLAS ESTRICTAS PARA LA ACCIÓN:
    - Usa 'save' SOLAMENTE si el usuario te envía notas, ideas, código o enlaces para guardar.
    - Usa 'ask_user' SIEMPRE que el usuario te haga una pregunta conversacional o te pida buscar algo.
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

async def answer_question_with_context(question: str, knowledge_context: str) -> str:
    """Genera una respuesta basada en las notas leídas de GitHub."""
    prompt = f"""
    Eres un asistente inteligente de un 'Segundo Cerebro'. 
    Responde a la pregunta del usuario utilizando ÚNICAMENTE el siguiente contexto de sus notas guardadas.
    Si la respuesta no está en estas notas, indícalo amablemente.

    NOTAS GUARDADAS DEL USUARIO:
    {knowledge_context}
    """
    
    completion = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": question}
        ],
        temperature=0.2
    )
    return completion.choices[0].message.content