import aiosqlite
from datetime import datetime

DB_NAME = "bot_memory.db"

async def init_db():
    """Crea la tabla de historial si no existe."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                timestamp DATETIME
            )
        """)
        await db.commit()
        print("Base de datos SQLite inicializada.")

async def save_message(user_id: int, role: str, content: str):
    """Guarda un mensaje en la base de datos (role puede ser 'user' o 'assistant')."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO chat_history (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, role, content, datetime.now())
        )
        await db.commit()

async def get_chat_history(user_id: int, limit: int = 5) -> list:
    """Recupera los últimos N mensajes de un usuario para dárselos de contexto al Agente."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            """
            SELECT role, content FROM (
                SELECT id, role, content FROM chat_history 
                WHERE user_id = ? 
                ORDER BY timestamp DESC LIMIT ?
            ) ORDER BY id ASC
            """, 
            (user_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            
    # Formateamos el historial para que OpenAI lo entienda
    history = [{"role": row[0], "content": row[1]} for row in rows]
    return history