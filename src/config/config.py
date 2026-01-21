import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Rutas del proyecto
BASE_DIR = Path(__file__).parent.parent.parent
CSV_DIR = BASE_DIR / "data" / "csv"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
CHROMA_DIR = BASE_DIR / "chroma_db"
# CHROMA_DIR2 points to the same folder as CHROMA_DIR now, keeping variable for compatibility
CHROMA_DIR2 = CHROMA_DIR

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

MODEL_NAME = os.getenv("MODEL_NAME", "xiaomi/mimo-v2-flash:free")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"

# Ruta de mi carpeta : cd C:\Users\danie\TFG_Scraper
# Comando activar env: .\venv\Scripts\activate