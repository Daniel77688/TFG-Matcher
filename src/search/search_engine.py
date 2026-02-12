"""
Motor de búsqueda semántica sobre ChromaDB.

Proporciona búsqueda por query, filtros, perfiles de profesores y estadísticas
con caché TTL para evitar recalcular en cada request.
"""
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.utils.text_utils import normalize_text

logger = logging.getLogger(__name__)

# ── Constantes de metadatos ─────────────────────────────────────────
KEY_PROFESOR = "profesor"
KEY_TIPO_PRODUCCION = "tipo_produccion"
KEY_FECHA = "fecha"
KEY_IF_SJR = "if_sjr"
KEY_CATEGORIAS = "categorias"
KEY_Q_SJR = "q_sjr"

MAX_RESULTS = 100
STATS_CACHE_TTL = 300  # 5 minutos


class SearchEngine:
    """Motor de búsqueda semántica sobre la colección de ChromaDB."""

    def __init__(self, chroma_collection):
        if chroma_collection is None:
            raise ValueError("La colección de ChromaDB no puede ser None")
        self.collection = chroma_collection
        self._stats_cache: Optional[Dict] = None
        self._stats_cache_time: float = 0

    # ── Búsqueda principal ──────────────────────────────────────────

    def search(
        self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Realiza una búsqueda semántica con filtros opcionales."""
        if not self.collection:
            raise RuntimeError("ChromaDB no está inicializado")

        limit = max(1, min(limit, MAX_RESULTS))
        where_clause = self._build_where_clause(filters)
        normalized_query = normalize_text(query)

        results = self.collection.query(
            query_texts=[normalized_query],
            n_results=limit,
            where=where_clause if where_clause else None,
            include=["metadatas", "documents", "distances"],
        )

        processed = self._process_search_results(results, filters)

        return {
            "query": query,
            "total_results": len(processed),
            "results": processed,
            "filters_applied": filters or {},
        }

    @staticmethod
    def _build_where_clause(filters: Optional[Dict[str, Any]]) -> Dict:
        """Construye la cláusula WHERE para ChromaDB a partir de los filtros."""
        if not filters:
            return {}

        where = {}
        if KEY_PROFESOR in filters:
            where[KEY_PROFESOR] = filters[KEY_PROFESOR]
        if KEY_TIPO_PRODUCCION in filters:
            where[KEY_TIPO_PRODUCCION] = normalize_text(filters[KEY_TIPO_PRODUCCION])
        if KEY_Q_SJR in filters:
            where[KEY_Q_SJR] = filters[KEY_Q_SJR]
        return where

    def _process_search_results(
        self, chroma_results: Dict, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Procesa los resultados crudos de ChromaDB en un formato limpio."""
        results = []

        if not chroma_results["ids"] or not chroma_results["ids"][0]:
            return results

        for i, doc_id in enumerate(chroma_results["ids"][0]):
            metadata = chroma_results["metadatas"][0][i]
            document = chroma_results["documents"][0][i]
            distance = chroma_results["distances"][0][i]

            # Filtros post-query (rango de fechas, IF mínimo)
            if filters and not self._passes_post_filters(metadata, filters):
                continue

            relevance_score = max(0, 1 - distance)

            results.append({
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
                "q_sjr": metadata.get(KEY_Q_SJR, ""),
            })

        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results

    @staticmethod
    def _passes_post_filters(metadata: Dict, filters: Dict) -> bool:
        """Verifica si un resultado pasa los filtros que ChromaDB no puede aplicar nativamente."""
        # Filtro por rango de fechas
        if "fecha_range" in filters and metadata.get(KEY_FECHA):
            fecha = metadata[KEY_FECHA]
            inicio = filters["fecha_range"].get("inicio")
            fin = filters["fecha_range"].get("fin")
            if inicio and fecha < inicio:
                return False
            if fin and fecha > fin:
                return False

        # Filtro por factor de impacto mínimo
        if "min_if_sjr" in filters and metadata.get(KEY_IF_SJR):
            try:
                if float(metadata[KEY_IF_SJR]) < filters["min_if_sjr"]:
                    return False
            except (ValueError, TypeError):
                return False

        return True

    # ── Listado de profesores ───────────────────────────────────────

    def get_all_profesores(self) -> Dict[str, Any]:
        """Devuelve una lista ordenada de todos los profesores con estadísticas."""
        all_results = self.collection.get(include=["metadatas"])
        profesores_data: Dict[str, Dict] = {}

        for metadata in all_results["metadatas"]:
            profesor = metadata.get(KEY_PROFESOR)
            if not profesor:
                continue

            if profesor not in profesores_data:
                profesores_data[profesor] = {
                    "name": profesor,
                    "username": metadata.get("profesor_username", ""),
                    "total_works": 0,
                    "work_types": {},
                    "categories": set(),
                }

            profesores_data[profesor]["total_works"] += 1

            tipo_prod = metadata.get(KEY_TIPO_PRODUCCION, "Unknown")
            profesores_data[profesor]["work_types"][tipo_prod] = (
                profesores_data[profesor]["work_types"].get(tipo_prod, 0) + 1
            )

            if metadata.get(KEY_CATEGORIAS):
                profesores_data[profesor]["categories"].add(metadata[KEY_CATEGORIAS])

        # Convertir sets a listas
        for data in profesores_data.values():
            data["categories"] = list(data["categories"])

        sorted_profesores = sorted(
            profesores_data.values(), key=lambda x: x["total_works"], reverse=True
        )

        return {
            "total_profesores": len(sorted_profesores),
            "profesores": sorted_profesores,
        }

    # ── Perfil de profesor ──────────────────────────────────────────

    def get_profesor_profile(self, profesor_name: str) -> Optional[Dict[str, Any]]:
        """Devuelve el perfil completo de un profesor con estadísticas y trabajos."""
        results = self.collection.get(
            where={KEY_PROFESOR: profesor_name},
            include=["metadatas", "documents"],
        )

        if not results["ids"]:
            return None

        works = []
        estadisticas = {
            "total_trabajos": len(results["ids"]),
            "tipos_produccion": {},
            "años_activo": set(),
            "categorias": set(),
            "fuentes": set(),
            "trabajos_recientes": [],
            "docencia": [],
            "investigacion": [],
            "proyectos": [],
        }

        for i, doc_id in enumerate(results["ids"]):
            metadata = results["metadatas"][i]
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
                "content": document,
            }
            works.append(work)

            # Estadísticas
            tipo_prod = metadata.get(KEY_TIPO_PRODUCCION, "Unknown")
            estadisticas["tipos_produccion"][tipo_prod] = (
                estadisticas["tipos_produccion"].get(tipo_prod, 0) + 1
            )

            if metadata.get(KEY_FECHA):
                try:
                    estadisticas["años_activo"].add(metadata[KEY_FECHA][:4])
                except (IndexError, TypeError):
                    pass

            if metadata.get(KEY_CATEGORIAS):
                estadisticas["categorias"].add(metadata[KEY_CATEGORIAS])
            if metadata.get("fuente"):
                estadisticas["fuentes"].add(metadata["fuente"])

            # Clasificación por tipo
            tipo_lower = tipo_prod.lower()
            if "docencia" in tipo_lower:
                estadisticas["docencia"].append(work)
            elif "proyecto" in tipo_lower:
                estadisticas["proyectos"].append(work)
            else:
                estadisticas["investigacion"].append(work)

        # Ordenar por fecha
        works.sort(key=lambda x: self._safe_parse_date(x["fecha"]), reverse=True)
        estadisticas["trabajos_recientes"] = works[:10]

        # Sets → listas
        estadisticas["años_activo"] = sorted(list(estadisticas["años_activo"]), reverse=True)
        estadisticas["categorias"] = list(estadisticas["categorias"])
        estadisticas["fuentes"] = list(estadisticas["fuentes"])

        return {
            "profesor": profesor_name,
            "works": works,
            "estadisticas": estadisticas,
        }

    # ── Estadísticas (con caché) ────────────────────────────────────

    def get_database_stats(self) -> Dict[str, Any]:
        """Devuelve estadísticas globales con caché TTL de 5 minutos."""
        now = time.time()
        if self._stats_cache and (now - self._stats_cache_time) < STATS_CACHE_TTL:
            return self._stats_cache

        all_data = self.collection.get(include=["metadatas"])

        if not all_data["ids"]:
            empty_stats = {
                "total_documents": 0,
                "total_profesores": 0,
                "tipos_produccion": {},
                "años_cubiertos": [],
                "años_publicacion": {},
                "categorias_populares": {},
            }
            self._stats_cache = empty_stats
            self._stats_cache_time = now
            return empty_stats

        tipos_produccion: Dict[str, int] = {}
        años: set = set()
        años_publicacion: Dict[str, int] = {}
        categorias: Dict[str, int] = {}
        profesores: set = set()

        for metadata in all_data["metadatas"]:
            tipo_prod = metadata.get(KEY_TIPO_PRODUCCION, "Unknown")
            tipos_produccion[tipo_prod] = tipos_produccion.get(tipo_prod, 0) + 1

            if metadata.get(KEY_FECHA):
                try:
                    y = metadata[KEY_FECHA][:4]
                    años.add(y)
                    años_publicacion[y] = años_publicacion.get(y, 0) + 1
                except (IndexError, TypeError):
                    pass

            categoria = metadata.get(KEY_CATEGORIAS, "Unknown")
            categorias[categoria] = categorias.get(categoria, 0) + 1

            if metadata.get(KEY_PROFESOR):
                profesores.add(metadata[KEY_PROFESOR])

        stats = {
            "total_documents": len(all_data["ids"]),
            "total_profesores": len(profesores),
            "tipos_produccion": dict(
                sorted(tipos_produccion.items(), key=lambda x: x[1], reverse=True)
            ),
            "años_cubiertos": sorted(list(años), reverse=True),
            "años_publicacion": dict(
                sorted(años_publicacion.items(), key=lambda x: x[0], reverse=True)
            ),
            "categorias_populares": dict(
                sorted(categorias.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
        }

        self._stats_cache = stats
        self._stats_cache_time = now
        return stats

    # ── RAG: Documentos de profesor ──────────────────────────────────

    def get_professor_documents(self, profesor_name: str, limit: int = 20) -> List[str]:
        """Devuelve los textos de los documentos de un profesor para RAG."""
        results = self.collection.get(
            where={KEY_PROFESOR: profesor_name},
            include=["documents", "metadatas"],
        )
        if not results["documents"]:
            return []

        # Ordenar por fecha (más recientes primero) y limitar
        items = list(zip(results["documents"], results["metadatas"]))
        items.sort(
            key=lambda x: self._safe_parse_date(x[1].get(KEY_FECHA, "")),
            reverse=True,
        )
        return [doc for doc, _ in items[:limit]]

    def get_all_professor_names(self) -> List[str]:
        """Devuelve una lista de todos los nombres de profesores."""
        all_data = self.collection.get(include=["metadatas"])
        names = set()
        for meta in all_data["metadatas"]:
            prof = meta.get(KEY_PROFESOR)
            if prof:
                names.add(prof)
        return sorted(names)

    # ── Ranking de disponibilidad ─────────────────────────────────────

    def get_availability_ranking(self) -> List[Dict[str, Any]]:
        """Calcula ranking de disponibilidad simulada de cada profesor."""
        all_data = self.collection.get(include=["metadatas"])
        professors: Dict[str, Dict] = {}
        current_year = datetime.now().year

        for meta in all_data["metadatas"]:
            prof = meta.get(KEY_PROFESOR)
            if not prof:
                continue
            if prof not in professors:
                professors[prof] = {
                    "profesor": prof,
                    "total_publications": 0,
                    "recent_publications": 0,
                    "categories": set(),
                }
            professors[prof]["total_publications"] += 1

            # Publicaciones de los últimos 3 años
            fecha = meta.get(KEY_FECHA, "")
            if fecha:
                try:
                    year = int(fecha[:4])
                    if current_year - year <= 3:
                        professors[prof]["recent_publications"] += 1
                except (ValueError, IndexError):
                    pass

            if meta.get(KEY_CATEGORIAS):
                professors[prof]["categories"].add(meta[KEY_CATEGORIAS])

        # Calcular score de disponibilidad (inverso de carga reciente)
        max_recent = max((p["recent_publications"] for p in professors.values()), default=1) or 1

        ranking = []
        for data in professors.values():
            load = data["recent_publications"] / max_recent
            availability_score = round(1.0 - (load * 0.7), 2)

            if availability_score >= 0.7:
                label = "Alta"
            elif availability_score >= 0.4:
                label = "Media"
            else:
                label = "Baja"

            ranking.append({
                "profesor": data["profesor"],
                "total_publications": data["total_publications"],
                "recent_publications": data["recent_publications"],
                "categories": list(data["categories"]),
                "availability_score": availability_score,
                "availability_label": label,
            })

        ranking.sort(key=lambda x: x["availability_score"], reverse=True)
        return ranking

    # ── Utilidades ──────────────────────────────────────────────────

    @staticmethod
    def _safe_parse_date(fecha_str: str) -> datetime:
        """Parsea una fecha de forma segura, devolviendo datetime.min si falla."""
        if not fecha_str or fecha_str in ["-", "", "N/A", "n/a"]:
            return datetime.min

        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m", "%Y"]:
            try:
                return datetime.strptime(fecha_str, fmt)
            except (ValueError, TypeError):
                continue
        return datetime.min
