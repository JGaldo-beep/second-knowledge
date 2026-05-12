import os
from github import Github
from github import Auth
from dotenv import load_dotenv

load_dotenv()

auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
g = Github(auth=auth)
repo_name = os.getenv("GITHUB_REPO")

def save_to_github(topic: str, tags: list, summary: str, original_content: str, source_type: str):
    """Guarda o actualiza un archivo Markdown en el repositorio de GitHub."""
    repo = g.get_repo(repo_name)
    file_path = f"{topic}.md"
    
    new_entry = f"\n\n---\n### Nuevo Registro ({source_type})\n**Etiquetas:** {', '.join(tags)}\n**Resumen:** {summary}\n\n**Contenido Original:**\n{original_content}\n"

    try:
        contents = repo.get_contents(file_path)
        updated_content = contents.decoded_content.decode("utf-8") + new_entry
        
        repo.update_file(
            path=contents.path,
            message=f"Añadiendo nuevo conocimiento a {topic}",
            content=updated_content,
            sha=contents.sha
        )
        print(f"Archivo {file_path} actualizado en GitHub.")
        
    except Exception as e:
        print(f"Archivo {file_path} no encontrado. Creando nuevo...")
        initial_content = f"# {topic}\n\nRepositorio de conocimientos sobre {topic}." + new_entry
        
        repo.create_file(
            path=file_path,
            message=f"Creando nuevo tema: {topic}",
            content=initial_content
        )
        print(f"✨ Archivo {file_path} creado exitosamente.")

def get_from_github(topic: str):
    """Busca y lee un archivo Markdown en el repositorio de GitHub."""
    repo = g.get_repo(repo_name)
    file_path = f"{topic}.md"
    
    try:
        contents = repo.get_contents(file_path)
        return contents.decoded_content.decode("utf-8")
    except Exception:
        # Si el archivo no existe, devuelve None
        return None