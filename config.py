import os 
from pathlib import Path

# Rutas del proyecto
BASE_DIR = Path(__file__).parent
CSV_DIR = BASE_DIR / "data" / "csv"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
CHROMA_DIR = BASE_DIR / "chroma_db"

# Chromadb configuración
COLLECTION_NAME = "profesores_tfg"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Campos necesarios del CSV
RELEVANT_FIELDS = [
    "TÍTULO",
    "AUTORES",  
    "FECHA",
    "IDENTIFICADOR",
    "TIPO",
    "TIPO DE PRODUCCIÓN",
    "CATEGORÍAS",
    "FUENTE",
    "IF SJR",
    "Q SJR"
]