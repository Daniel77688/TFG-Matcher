import uuid # Para generar IDs unicos
from pathlib import Path
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import pandas as pd
from src.config.config import CSV_DIR, CHROMA_DIR2, EMBEDDING_MODEL, COLLECTION_NAME

# =========================================================================================
# 1. Carga y procesa CSVs:                               load_all_csvs + _process_dataframe
# 2. Crear o reiniciar una coleccion en Chroma:          setup_chroma_collection
# 3. Insertar documentos y embeddings en la coleccion:   load_data_to_chroma
# =========================================================================================

class DataProcessorPandas:
    def __init__(self):
        self.model = SentenceTransformer(EMBEDDING_MODEL) # Aqui cargamos el modelo de IA : Convierte texto a vectores numericos.Any
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DIR2),
            settings=Settings(anonymized_telemetry=False)
        ) # Conexion con la BD de forma persistente y asi no se borran los datos a pesar de apagar el PC


    def load_all_csvs(self) -> Tuple[List[str], List[str], List[Dict], List[List[float]]]:
        all_ids = []
        all_documents = []
        all_metadatas = []
        all_embeddings = []

        csv_files = list(CSV_DIR.glob("*.csv"))
        print(f"> Se encontraron {len(csv_files)} CSV files...")

        for csv_file in csv_files:
            print(f"    - Procesando {csv_file.name} (con Pandas)")
            try:
                df = pd.read_csv(csv_file, encoding='utf-8', on_bad_lines='skip')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(csv_file, encoding='latin-1', on_bad_lines='skip')
                except Exception as e:
                    print(f"      ! Error leyendo {csv_file.name}: {e}")
                    continue

            # Limpieza básica: Eliminamos columnas vacías o filas totalmente vacías
            df.dropna(how='all', inplace=True)
            
            # [EXPLICACION]: En lugar de limpiar espacios fila por fila:
            #   cleaned_key = key.strip().upper()
            # Pandas nos permite limpiar todos los nombres de columnas de golpe:
            df.columns = df.columns.astype(str).str.strip().str.upper()
            
            # Y limpiar todos los valores de texto del dataframe de una sola vez:
            df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            df.fillna("", inplace=True) # Reemplazamos Nones/NaNs con cadena vacía

            # Preparamos los datos
            ids, documents, metadatas = self._process_dataframe(df, csv_file)
            
            if not documents:
                continue

            # [EXPLICACION - VELOCIDAD]: Aquí está la magia.
            # Aquí tienes una lista de textos y se la pasas TODA DE GOLPE al modelo.
            # El modelo puede procesar en paralelo internamente. Es mucho más rápido.
            embeddings = self.model.encode(documents).tolist()

            all_ids.extend(ids)
            all_documents.extend(documents)
            all_metadatas.extend(metadatas)
            all_embeddings.extend(embeddings)

        return all_ids, all_documents, all_metadatas, all_embeddings

    def _process_dataframe(self, df: pd.DataFrame, csv_path: Path) -> Tuple[List[str], List[str], List[Dict]]:
        ids = []
        documents_text = []
        metadatas = []

        nombre_profesor = csv_path.stem.replace("_", " ").title()
        
        # Mapa de columnas para el texto semántico
        campo_map = {
            "TÍTULO": "Título",
            "AUTORES": "Autores",
            "TIPO": "Tipo",
            "TIPO DE PRODUCCIÓN": "Tipo de producción",
            "CATEGORÍAS": "Categorías",
            "FUENTE": "Fuente",
            "IF SJR": "Impacto SJR",
            "Q SJR": "Cuartil SJR"
        }

        # [EXPLICACION]: Iteramos sobre el DataFrame. 
        # Aunque seguimos usando un bucle, iterar sobre filas en memoria ya limpia es rápido.
        for index, row in df.iterrows():
            # Construcción del texto semántico
            # Equivalente a tu método _build_semantic_text
            partes = []
            for col_csv, col_display in campo_map.items():
                if col_csv in df.columns and row[col_csv]:
                    partes.append(f"{col_display}: {row[col_csv]}")
            
            semantic_text = " ".join(partes)

            if not semantic_text.strip():
                continue

            # Construcción de metadatos (Igual que tu _extract_relevant_info)
            # Nota: Pandas usa 'get' de forma similar a los diccionarios si convertimos la serie,
            # pero aquí accedemos directamente con seguridad.
            metadata = {
                "profesor": nombre_profesor,
                "profesor_username": nombre_profesor.lower().replace(" ", "."),
                "titulo": str(row.get("TÍTULO", "")),
                "autores": str(row.get("AUTORES", "")),
                "fecha": str(row.get("FECHA", "")),
                "tipo": str(row.get("TIPO", "")),
                "tipo_produccion": str(row.get("TIPO DE PRODUCCIÓN", "")),
                "categorias": str(row.get("CATEGORÍAS", "")),
                "fuente": str(row.get("FUENTE", "")),
                "if_sjr": str(row.get("IF SJR", "")),
                "q_sjr": str(row.get("Q SJR", "")),
                "csv_file": csv_path.name,
                "row_number": index # Pandas mantiene el índice original
            }

            ids.append(str(uuid.uuid4()))
            documents_text.append(semantic_text)
            metadatas.append(metadata)

        return ids, documents_text, metadatas

    def setup_chroma_collection(self):
        # Este método es IDÉNTICO al original. Pandas solo cambia CÓMO leemos los datos,
        # no DÓNDE los guardamos.
        try:
            self.client.delete_collection(COLLECTION_NAME)
            print(f"> Coleccion '{COLLECTION_NAME}' eliminada.")
        except:
            print(f"> Coleccion '{COLLECTION_NAME}' no existe. Creando una nueva...")
        
        coleccion = self.client.create_collection(
                name=COLLECTION_NAME,
                metadata={
                    "description": "Base de datos de profesores URJC para busqueda de tutor en TFGs y TFMs",
                    "model": EMBEDDING_MODEL
                }
            )    
        return coleccion
    
    def load_data_to_chroma(self, batch_size: int = 1000):
        # También IDÉNTICO al original en lógica.
        # Llamamos a nuestra versión Pandas de load_all_csvs
        ids, documents, metadatas, embeddings = self.load_all_csvs()

        if not ids:
            print("ERROR: No hay datos para cargar.")
            return
        
        coleccion = self.setup_chroma_collection()

        print(f"> Cargando {len(ids)} documentos en lotes de {batch_size}...")
        for i in range(0, len(ids), batch_size):
            batch_end = min(i + batch_size, len(ids))
            batch_num = i // batch_size + 1
            print(f"    - Cargando lote {batch_num}: {i+1}-{batch_end}")
                
            coleccion.add(
                ids=ids[i:batch_end],
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end],
                embeddings=embeddings[i:batch_end]    
            )

        print(f"> Carga completa en ChromaDB. Total de documentos cargados: {coleccion.count()}")
        return coleccion
    


def get_chroma_collection():                          # Obtener la coleccion de ChromaDB
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR2),
        settings=Settings(anonymized_telemetry=False)
    )
    try:
        return client.get_collection(COLLECTION_NAME)
    except:
        print(f"ERROR: La colección '{COLLECTION_NAME}' no existe.")
        return None    
