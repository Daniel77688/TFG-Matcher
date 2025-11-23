import csv                                            # para leer archivos CSV
import uuid                                           # para generar IDs únicos
from pathlib import Path
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer # para generar embeddings
import chromadb                                       # para la base de datos de vectores
from chromadb.config import Settings                  # para configurar chromadb
from config import CSV_DIR, CHROMA_DIR, EMBEDDING_MODEL, RELEVANT_FIELDS, COLLECTION_NAME

class DataProcessor:
    def __init__(self):
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.client = chromadb.PersistentClient( # Para que sea persistente no solo en la RAM
            path=str(CHROMA_DIR),                # ruta donde se almacenaran los datos
            settings=Settings(
                anonymized_telemetry=False       # desactivar estadisticas
            )
        )

    def process_csv_file(self, csv_path: Path) -> List[Dict[str, Any]]:        # Procesar archivo CSV y extraer informacion relevante
        documents = []                                                          # Lista para almacenar los documentos procesados
        
        for encoding in ['utf-8', 'latin-1']:                                      # Intentar con diferentes codificaciones
            try:                                                                    # Abrir y leer el archivo CSV
                with open(csv_path, 'r', newline='', encoding=encoding) as file:
                    reader = csv.DictReader(file, delimiter=',')                                    # Leer el CSV como un diccionario {columna : valor}
                    for row_num, row in enumerate(reader):                                          # Iterar sobre cada fila del CSV y devvuelve pares (numero de fila -> indice, fila -> diccionario)
                        cleaned_row = {}                                                            # Diccionario para almacenar la fila limpia
                        for key, value in row.items():                                              # Limpiar claves y valores
                            if key and key.strip().upper() in RELEVANT_FIELDS:
                                cleaned_key = key.strip().upper()                                   # Eliminar espacios y convertir a mayusculas las columnas
                                cleaned_row[cleaned_key] = (value or "").strip()                    # Eliminar espacios de los valores y para valores nulos asignar cadena vacia
                        
                        doc_data = self._extract_relevant_info(cleaned_row, csv_path, row_num)
                        if doc_data:
                            documents.append(doc_data)                                              # Añadir el documento procesado a la lista

            except UnicodeDecodeError:
                continue

        return documents                                                        # Devuelve la lista de documentos procesados
    

    def _extract_relevant_info(self, row: Dict[str, str], csv_path: Path, row_num: int) -> Dict[str, Any]:  # Extraer la informacion relevante de una fila CSV
        nombre_profesor = csv_path.stem.replace("_", "").title()             # Obtener el nombre del profesor del nombre del archivo

        semantic_text = self._build_semantic_text(row)                       # Convierte en un texto liso la informacion relevante para sacar embeddings

        if not semantic_text.strip():                                        # Si el texto semantico esta vacio no hay que procesar esta fila
            return None
        
        
        metadata = {field.lower().replace(" ", "_"): row.get(field, "") for field in RELEVANT_FIELDS}
        metadata.update({
            "profesor": nombre_profesor,
            "profesor_username": nombre_profesor.lower().replace(" ", "."),
            "csv_file": csv_path.name,
            "row_number": row_num
        })                                                                   # Construir los metadatos del documento

        return {
            "id": str(uuid.uuid4()),                                         # Generar un ID unico para el documento
            "text": semantic_text,                                           # Texto semantico para embeddings
            "metadata": metadata,                                            # Metadatos asociados
            "profesor": nombre_profesor                                      # Nombre del profesor
        }
    
    def _build_semantic_text(self, row: Dict[str, str]) -> str:         # Construir el texto semantico a partir de los campos relevantes
        partes = []                                                     # Lista para almacenar las partes del texto
        
        for campo in RELEVANT_FIELDS:                                   # Iterar sobre los campos relevantes
            if(row.get(campo)):                                         # Si el campo existe y no es vacio
                partes.append(f"{campo.title()}: {row[campo]}")         # Añadir el campo y su valor al texto semantico
        
        return " ".join(partes)                                         # Unir todas las partes en un solo texto separado por espacios          


    def load_all_csvs(self) -> Tuple[List[str], List[str], List[Dict], List[List[float]]]:
        ids, documents, metadatas, embeddings = [], [], [], []

        csv_files = list(CSV_DIR.glob("*.csv"))                          # Obtener todos los archivos CSV del directorio
        print(f"> Se encontraron {len(csv_files)} CSV files...")

        for csv in csv_files:
            print(f"    - Procesando {csv.name}")
            docs = self.process_csv_file(csv)                           # Procesar cada archivo CSV

            for doc in docs:                                             # Sobre los documentos procesados
                embedding = self.model.encode(doc["text"]).tolist()      # Generar el embedding del texto semantico en lista de floats

                ids.append(doc["id"])                                   # Añadir el ID
                documents.append(doc["text"])                           # Añadir el texto
                metadatas.append(doc["metadata"])                       # Añadir los metadatos
                embeddings.append(embedding)                            # Añadir el embedding

        return ids, documents, metadatas, embeddings


    def setup_chroma_collection(self):                              # Configurar la coleccion de ChromaDB
        try:
            self.client.delete_collection(COLLECTION_NAME)          # Eliminar la coleccion si ya existe
            print(f"> Coleccion '{COLLECTION_NAME}' eliminada.")
        except:
            print(f"> Coleccion '{COLLECTION_NAME}' no existe. Creando una nueva...")
        
        coleccion = self.client.create_collection(              # Crear una nueva coleccion
                name=COLLECTION_NAME,
                metadata={
                    "description": "Base de datos de profesores URJC para busqueda de tutor en TFGs y TFMs",
                    "model": EMBEDDING_MODEL
                }
            )    

        return coleccion
    
    def load_data_to_chroma(self, batch_size: int = 1000):             # Cargar los datos 1000 por tanda, si se cargan mas de aprox 5000 peta.
        ids, documents, metadatas, embeddings = self.load_all_csvs()   # Cargar todos los datos de los CSVs

        if not ids:
            print("ERROR: No hay datos para cargar.")
            return
        
        coleccion = self.setup_chroma_collection()                    # Configurar la coleccion de ChromaDB

        print(f"> Cargando {len(ids)} documentos en lotes de {batch_size}...")
        for i in range(0, len(ids), batch_size):
            batch_end = min(i + batch_size, len(ids))
            batch_num = i // batch_size + 1
            print(f"    - Cargando lote {batch_num}: {i+1}-{batch_end}")
                
            coleccion.add(                                            # Añadir el lote a la coleccion
                ids=ids[i:batch_end],
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end],
                embeddings=embeddings[i:batch_end]    
            )

        print("> Carga completa en ChromaDB. Total de documentos cargados:", {coleccion.count()})
        return coleccion
    

    def get_chroma_collection():                          # Obtener la coleccion de ChromaDB
        client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False)
        )
        try:
            return client.get_collection(COLLECTION_NAME)
        except:
            print(f"ERROR: La colección '{COLLECTION_NAME}' no existe.")
            return None