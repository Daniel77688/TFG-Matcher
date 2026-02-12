import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Rutas del proyecto ──────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent.parent
CSV_DIR = BASE_DIR / "data" / "csv"
# Directorio demo (fallback cuando data/csv está vacío)
DEMO_CSV_DIR = BASE_DIR / "frontend" / "static" / "data"
CHROMA_DIR = BASE_DIR / "chroma_db"
DB_PATH = BASE_DIR / "users.db"

# ── ChromaDB ────────────────────────────────────────────────────────
COLLECTION_NAME = "profesores_tfg"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ── Campos relevantes del CSV ───────────────────────────────────────
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
    "Q SJR",
]

# ── LLM (OpenRouter) ───────────────────────────────────────────────
MODEL_NAME = os.getenv("MODEL_NAME", "xiaomi/mimo-v2-flash:free")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"

# ── JWT ─────────────────────────────────────────────────────────────
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "tfg-scraper-secret-change-in-production")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))