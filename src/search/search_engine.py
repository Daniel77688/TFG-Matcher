from typing import List, Dict, Any
from datetime import datetime

KEY_PROFESOR = "profesor"
KEY_TIPO_PRODUCCION = "tipo_produccion"
KEY_FECHA = "fecha"
KEY_IF_SJR = "if_sjr"
KEY_CATEGORIAS = "categorias"
KEY_Q_SJR = "q_sjr"

MAX_RESULTS = 100 

class SearchEngine:
    def __init__(self, chroma_collection):   # Constructor que recibe la colección de Chroma
        if chroma_collection is None:
            raise ValueError("ERROR: La coleccion de Chroma no está cargada.")

        self.collection = chroma_collection


    def search(self, query: str, limit: int = 10, filters: Dict[str, Any] = None) -> Dict[str, Any]:        
        if not self.collection:
            raise RuntimeError("ERROR: ChromaDB no está inicializado.")
        
        limit = min(limit, MAX_RESULTS)                                       # Limitamos el número máximo de resultados

        where_clause = {}                                                     # Para los filtros

        if filters:                                                           # Si hay filtros, los agregamos al where_clause
            if KEY_PROFESOR  in filters:
                where_clause[KEY_PROFESOR ] = filters[KEY_PROFESOR ]
            if KEY_TIPO_PRODUCCION in filters:
                where_clause[KEY_TIPO_PRODUCCION] = filters[KEY_TIPO_PRODUCCION]
            if KEY_Q_SJR in filters:
                where_clause[KEY_Q_SJR] = filters[KEY_Q_SJR]

        results = self.collection.query(                                      # Realizamos la consulta a la colección
            query_texts=[query],
            n_results=limit,
            where=where_clause if where_clause else None,
            include=["metadatas", "documents", "distances"]
        )

        resultados_procesado = self._process_search_results(results, filters) # Procesamos los resultados

        return {
            "query": query,
            "total_results": len(resultados_procesado),
            "results": resultados_procesado,
            "filters_applied": filters or {}
        }
    

    def _process_search_results(self, chroma_results: Dict, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []                                                   # Lista para almacenar los resultados procesados

        if not chroma_results["ids"] or not chroma_results["ids"][0]:  # Si no hay resultados, retornamos la lista vacía
            return results

        for i, doc_id in enumerate(chroma_results["ids"][0]):          # Iteramos sobre los IDs de los documentos
            metadata = chroma_results["metadatas"][0][i]               # Obtenemos los metadatos del documento
            document = chroma_results["documents"][0][i]
            distance = chroma_results["distances"][0][i]

            if filters:
                if "fecha_range" in filters and metadata.get(KEY_FECHA):     # Filtrado por rango de fechas
                        fecha_result = metadata[KEY_FECHA]
                        fecha_inicio = filters["fecha_range"].get("inicio")
                        fecha_fin = filters["fecha_range"].get("fin")
                        
                        if fecha_inicio and fecha_result < fecha_inicio:
                            continue
                        if fecha_fin and fecha_result > fecha_fin:
                            continue      
                
                if "min_if_sjr" in filters and metadata.get(KEY_IF_SJR):     # Filtrado por factor de impacto SJR mínimo
                        try:
                            if_sjr = float(metadata[KEY_IF_SJR])
                            if if_sjr < filters["min_if_sjr"]:
                                continue
                        except (ValueError, TypeError):
                            continue

            relevance_score = max(0, 1 - distance)                     # Calculamos el puntaje de relevancia
                
            result = {                                                 # Construimos el diccionario del resultado
                "id": doc_id,
                "relevance_score": round(relevance_score, 3),
                "distance": round(distance, 3),
                "content": document,
                "metadata": metadata,
                "profesor": metadata.get(KEY_PROFESOR, "Unknown"),
                "titulo": metadata.get("titulo", ""),
                "tipo": metadata.get("tipo", ""),
                "tipo_produccion": metadata.get(KEY_TIPO_PRODUCCION, ""),
                "fecha": metadata.get(KEY_FECHA, ""),
                "categorias": metadata.get(KEY_CATEGORIAS, ""),
                "fuente": metadata.get("fuente", ""),
                "if_sjr": metadata.get(KEY_IF_SJR, ""),
                 "q_sjr": metadata.get(KEY_Q_SJR, "")
            }

            results.append(result)                                    # Agregamos el resultado a la lista

        results.sort(key=lambda x: x["relevance_score"], reverse=True)    # Ordenamos los resultados por puntaje de relevancia

        return results
    

    def get_all_profesores(self) -> Dict[str, Any]:
        if not self.collection:
            raise ValueError("ERROR: La coleccion de Chroma no está cargada.")

        all_results = self.collection.get(                                # Obtenemos todos los documentos de la colección
            include=["metadatas"]                                         # Incluir solo los metadatos
        )

        profesores_data = {}                                              # Para almacenar los profesores y sus producciones

        for metadata in all_results["metadatas"]:                         # Iteramos sobre los metadatos de cada documento
            profesor = metadata.get(KEY_PROFESOR)                           # Obtenemos el nombre del profesor
            if not profesor:
                continue

            if profesor not in profesores_data:                           # Si el profesor no está lo agregamos
                profesores_data[profesor] = {
                    "name": profesor,
                    "username": metadata.get("profesor_username", ""),
                    "total_works": 0,
                    "work_types": {},
                    "categories": set(),
                    "recent_works": []
                }
            profesores_data[profesor]["total_works"] += 1                 # Cada documento es un trabajo -> sumamos 1

            tipo_prod = metadata.get(KEY_TIPO_PRODUCCION, "Unknown")        # Contamos el tipo de producción/trabajo
            profesores_data[profesor]["work_types"][tipo_prod] = \
                profesores_data[profesor]["work_types"].get(tipo_prod, 0) + 1
            
            if metadata.get(KEY_CATEGORIAS):
                profesores_data[profesor]["categories"].add(metadata[KEY_CATEGORIAS]) # Agregamos la categoría al set


        for profesor_data in profesores_data.values():
            profesor_data["categories"] = list(profesor_data["categories"]) # Convertimos el set de categorías a lista


        sorted_profesores = sorted(                                       # Ordenamos los profesores por total de trabajos
            profesores_data.values(),
            key=lambda x: x["total_works"],
            reverse=True
        )

        return {                                                          # Retornamos el total de profesores y la lista ordenada con el total de trabajos
            "total_profesores": len(sorted_profesores),
            "profesores": sorted_profesores
        }
    
    def get_profesor_profile(self, profesor_name: str) -> Dict[str, Any]:
        results = self.collection.get(                              # Obtenemos todos los documentos del profesor
            where={KEY_PROFESOR: profesor_name},
            include=["metadatas", "documents"]
        )

        if not results["ids"]:
            return None
        
        works = []                                                  # Lista para almacenar los trabajos del profesor
        estadisticas = {                                            # Estadísticas iniciales del profesor
            "total_trabajos": len(results["ids"]),
            "tipos_produccion": {},
            "años_activo": set(),
            "categorias": set(),
            "fuentes": set(),
            "trabajos_recientes": [],
            "docencia": [],
            "investigacion": [],
            "proyectos": []
        }

        for i, doc_id in enumerate(results["ids"]):                 # Iteramos sobre los IDs de los documentos
            metadata = results["metadatas"][i]                      # Obtenemos los metadatos del documento
            document = results["documents"][i]

            work = {
                "id": doc_id,
                "titulo": metadata.get("titulo", ""),
                "tipo": metadata.get("tipo", ""),
                "tipo_produccion": metadata.get(KEY_TIPO_PRODUCCION, ""),
                "fecha": metadata.get(KEY_FECHA, ""),
                "categorias": metadata.get(KEY_CATEGORIAS, ""),
                "fuente": metadata.get("fuente", ""),
                "if_sjr": metadata.get(KEY_IF_SJR, ""),
                "q_sjr": metadata.get(KEY_Q_SJR, ""),
                "content": document
            }
            works.append(work)                                      # Agregamos el trabajo a la lista

            tipo_prod = metadata.get(KEY_TIPO_PRODUCCION, "Unknown")  # Contamos el tipo de producción/trabajo
            estadisticas["tipos_produccion"][tipo_prod] = \
                estadisticas["tipos_produccion"].get(tipo_prod, 0) + 1 
            

            if metadata.get(KEY_FECHA):                               # Extraemos el año de la fecha para los años activo
                try:
                    year = metadata[KEY_FECHA][:4]
                    estadisticas["años_activo"].add(year)
                except:
                    pass

            if metadata.get(KEY_CATEGORIAS):                          # Agregamos la categoría al set de categorías
                estadisticas["categorias"].add(metadata[KEY_CATEGORIAS])

            if metadata.get("fuente"):                              # Agregamos la fuente al set de fuentes
                estadisticas["fuentes"].add(metadata["fuente"])


            if "docencia" in tipo_prod.lower():                     # Clasificamos el trabajo según su tipo de producción
                estadisticas["docencia"].append(work)
            elif "proyecto" in tipo_prod.lower():
                estadisticas["proyectos"].append(work)
            else:
                estadisticas["investigacion"].append(work)
        
       
        def safe_parse_date(fecha_str):                                       # Función para parsear fechas de forma segura
            if not fecha_str or fecha_str in ["-", "", "N/A", "n/a"]:
                return datetime.min
            
            try:
                return datetime.strptime(fecha_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                # Intentar otros formatos comunes
                for fmt in ["%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m", "%Y"]:
                    try:
                        return datetime.strptime(fecha_str, fmt)
                    except:
                        continue
                return datetime.min
            
        works.sort(key=lambda x: safe_parse_date(x["fecha"]), reverse=True)  # Ordenamos los trabajos por fecha (más recientes primero)

        estadisticas["trabajos_recientes"] = works[:10]

        # Convertimos los sets a listas ya que chroma no acepta sets
        estadisticas["años_activo"] = sorted(list(estadisticas["años_activo"]), reverse=True)
        estadisticas["categorias"] = list(estadisticas["categorias"])
        estadisticas["fuentes"] = list(estadisticas["fuentes"])

        return {
            "profesor": profesor_name,
            "works": works,
            "estadisticas": estadisticas
        }


    def get_database_stats(self) -> Dict[str, Any]:
        all_data = self.collection.get(                               # Obtenemos todos los documentos de la colección
            include=["metadatas"]
        )

        if not all_data["ids"]:                                       # Si no hay datos devolvemos estadísticas vacías
            return {
                "total_documents": 0,
                "total_profesores": 0,
                "tipos_produccion": {},
                "años_cubiertos": [],
                "categorias_populares": {}
            }
        
        tipos_produccion = {}
        años = set()
        categorias = {}
        profesores = set()

        for metadata in all_data["metadatas"]:
            tipo_prod = metadata.get(KEY_TIPO_PRODUCCION, "Unknown")
            tipos_produccion[tipo_prod] = tipos_produccion.get(tipo_prod, 0) + 1

            if metadata.get(KEY_FECHA):
                try:
                    year = metadata[KEY_FECHA][:4]
                    años.add(year)
                except:
                    pass

            categoria = metadata.get(KEY_CATEGORIAS, "Unknown")
            categorias[categoria] = categorias.get(categoria, 0) + 1

            if metadata.get(KEY_PROFESOR):
                profesores.add(metadata[KEY_PROFESOR])
        return {
            "total_documents": len(all_data["ids"]),
            "total_profesores": len(profesores),
            "tipos_produccion": dict(sorted(tipos_produccion.items(), key=lambda x: x[1], reverse=True)),
            "años_cubiertos": sorted(list(años), reverse=True),
            "categorias_populares": dict(sorted(categorias.items(), key=lambda x: x[1], reverse=True)[:10])
        }

