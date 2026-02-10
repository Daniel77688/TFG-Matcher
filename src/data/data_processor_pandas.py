import uuid
from pathlib import Path
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import pandas as pd
import logging

from src.config.config import CSV_DIR, CHROMA_DIR, EMBEDDING_MODEL, COLLECTION_NAME
from src.utils.text_utils import normalize_text, generate_username

logger = logging.getLogger(__name__)

# =========================================================================================
# 1. Carga y procesa CSVs:                               load_all_csvs + _process_dataframe
# 2. Crear o reiniciar una coleccion en Chroma:          setup_chroma_collection
# 3. Insertar documentos y embeddings en la coleccion:   load_data_to_chroma
# =========================================================================================


class DataProcessorPandas:
    """Procesa archivos CSV de profesores y los carga en ChromaDB con embeddings semánticos."""

    def __init__(self):
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )

    def load_all_csvs(self) -> Tuple[List[str], List[str], List[Dict], List[List[float]]]:
        """Lee todos los CSV del directorio, genera texto semántico y embeddings."""
        all_ids: List[str] = []
        all_documents: List[str] = []
        all_metadatas: List[Dict] = []
        all_embeddings: List[List[float]] = []

        csv_files = list(CSV_DIR.glob("*.csv"))
        logger.info("Se encontraron %d archivos CSV", len(csv_files))

        for csv_file in csv_files:
            logger.info("Procesando %s (Pandas)", csv_file.name)
            try:
                df = pd.read_csv(csv_file, encoding="utf-8", on_bad_lines="skip")
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(csv_file, encoding="latin-1", on_bad_lines="skip")
                except Exception as e:
                    logger.warning("Error leyendo %s: %s", csv_file.name, e)
                    continue

            # Limpieza básica
            df.dropna(how="all", inplace=True)
            df.columns = df.columns.astype(str).str.strip().str.upper()
            df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            df.fillna("", inplace=True)

            ids, documents, metadatas = self._process_dataframe(df, csv_file)

            if not documents:
                continue

            # Encodear todos los documentos de golpe (mucho más rápido que uno a uno)
            embeddings = self.model.encode(documents).tolist()

            all_ids.extend(ids)
            all_documents.extend(documents)
            all_metadatas.extend(metadatas)
            all_embeddings.extend(embeddings)

        return all_ids, all_documents, all_metadatas, all_embeddings

    def _process_dataframe(
        self, df: pd.DataFrame, csv_path: Path
    ) -> Tuple[List[str], List[str], List[Dict]]:
        """Procesa un DataFrame y devuelve IDs, textos semánticos y metadatos."""
        ids: List[str] = []
        documents_text: List[str] = []
        metadatas: List[Dict] = []

        nombre_profesor = csv_path.stem.replace("_", " ").title()

        campo_map = {
            "TÍTULO": "Título",
            "AUTORES": "Autores",
            "TIPO": "Tipo",
            "TIPO DE PRODUCCIÓN": "Tipo de producción",
            "CATEGORÍAS": "Categorías",
            "FUENTE": "Fuente",
            "IF SJR": "Impacto SJR",
            "Q SJR": "Cuartil SJR",
        }

        for index, row in df.iterrows():
            # Construcción del texto semántico
            partes = []
            for col_csv, col_display in campo_map.items():
                if col_csv in df.columns and row[col_csv]:
                    partes.append(f"{col_display}: {row[col_csv]}")

            semantic_text = normalize_text(" ".join(partes))

            if not semantic_text:
                continue

            # Metadatos normalizados
            metadata = {
                "profesor": nombre_profesor,
                "profesor_username": generate_username(nombre_profesor),
                "titulo": normalize_text(str(row.get("TÍTULO", ""))),
                "autores": str(row.get("AUTORES", "")),
                "fecha": str(row.get("FECHA", "")),
                "tipo": str(row.get("TIPO", "")),
                "tipo_produccion": normalize_text(str(row.get("TIPO DE PRODUCCIÓN", ""))),
                "categorias": normalize_text(str(row.get("CATEGORÍAS", ""))),
                "fuente": str(row.get("FUENTE", "")),
                "if_sjr": str(row.get("IF SJR", "")),
                "q_sjr": str(row.get("Q SJR", "")),
                "csv_file": csv_path.name,
                "row_number": index,
            }

            ids.append(str(uuid.uuid4()))
            documents_text.append(semantic_text)
            metadatas.append(metadata)

        return ids, documents_text, metadatas

    def setup_chroma_collection(self):
        """Crea (o recrea) la colección en ChromaDB."""
        try:
            self.client.delete_collection(COLLECTION_NAME)
            logger.info("Colección '%s' eliminada", COLLECTION_NAME)
        except Exception:
            logger.info("Colección '%s' no existía, creando nueva...", COLLECTION_NAME)

        coleccion = self.client.create_collection(
            name=COLLECTION_NAME,
            metadata={
                "description": "Base de datos de profesores URJC para búsqueda de tutor TFG/TFM",
                "model": EMBEDDING_MODEL,
            },
        )
        return coleccion

    def load_data_to_chroma(self, batch_size: int = 1000):
        """Carga todos los datos procesados en ChromaDB por lotes."""
        ids, documents, metadatas, embeddings = self.load_all_csvs()

        if not ids:
            logger.error("No hay datos para cargar")
            return None

        coleccion = self.setup_chroma_collection()

        logger.info("Cargando %d documentos en lotes de %d...", len(ids), batch_size)
        for i in range(0, len(ids), batch_size):
            batch_end = min(i + batch_size, len(ids))
            batch_num = i // batch_size + 1
            logger.info("Cargando lote %d: %d-%d", batch_num, i + 1, batch_end)

            coleccion.add(
                ids=ids[i:batch_end],
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end],
                embeddings=embeddings[i:batch_end],
            )

        logger.info("Carga completa. Total documentos: %d", coleccion.count())
        return coleccion


def get_chroma_collection():
    """Obtiene la colección de ChromaDB existente (sin recrearla)."""
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    try:
        return client.get_collection(COLLECTION_NAME)
    except Exception:
        logger.error("La colección '%s' no existe. Ejecuta data_loader.py primero.", COLLECTION_NAME)
        return None
