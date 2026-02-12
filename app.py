"""
Backend FastAPI — TFG Scraper Pro
Sistema de recomendación de tutores TFG con IA y búsqueda semántica.
"""
import io
import os
import sys
import logging
import traceback
from datetime import datetime
from typing import Optional, List, Dict, Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, EmailStr

# ── Configurar path ─────────────────────────────────────────────────
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ── Logging profesional ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tfg_scraper")

# ── Imports internos ────────────────────────────────────────────────
from src.auth.auth import AuthSystem
from src.data.data_processor_pandas import get_chroma_collection
from src.search.search_engine import SearchEngine
from src.config.config import MODEL_NAME, OPENROUTER_API_KEY, BASE_URL


# ========== MODELOS PYDANTIC ==========

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    degree: Optional[str] = None
    year: Optional[int] = None
    interests: Optional[str] = None
    skills: Optional[str] = None
    preferred_areas: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    filters: Optional[Dict[str, Any]] = None

class ChatMessage(BaseModel):
    message: str
    user_id: int
    chat_history: Optional[List[Dict[str, str]]] = None
    last_feedback_positive: Optional[bool] = None  # True=útil, False=no útil, None=no respondió/prefiere no decir

class HistoryRequest(BaseModel):
    query: str
    search_type: str = "general"


# ========== INICIALIZACIÓN ==========

def create_app() -> FastAPI:
    """Crea y configura la aplicación FastAPI."""

    application = FastAPI(
        title="TFG Scraper Pro API",
        version="2.1.0",
        description="Sistema inteligente de recomendación de tutores TFG con búsqueda semántica e IA",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Archivos estáticos
    if os.path.exists("frontend"):
        application.mount("/static", StaticFiles(directory="frontend/static"), name="static")

    return application


app = create_app()

# ── Inicializar sistemas ────────────────────────────────────────────
auth_system = AuthSystem()
search_engine = None
llm = None

try:
    collection = get_chroma_collection()
    if collection:
        search_engine = SearchEngine(collection)
        logger.info("✅ SearchEngine cargado correctamente")
except Exception as e:
    logger.error("❌ Error cargando SearchEngine: %s", e)

try:
    if OPENROUTER_API_KEY:
        from langchain_openai import ChatOpenAI

        # Activamos el modo streaming para poder enviar tokens progresivamente al frontend.
        # Otros endpoints que usan llm.invoke seguirán funcionando igual, ya que LangChain
        # se encarga de agrupar los tokens internamente para esas llamadas.
        llm = ChatOpenAI(
            model=MODEL_NAME,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base=BASE_URL,
            temperature=0.7,
            streaming=True,
            max_tokens=800,
            timeout=30,
        )
        logger.info("✅ LLM configurado (streaming ON): %s", MODEL_NAME)
    else:
        logger.warning("⚠️ OPENROUTER_API_KEY no configurada")
except Exception as e:
    logger.error("❌ Error cargando LLM: %s", e)


# ========== UTILIDADES ==========

def _require_search_engine():
    """Lanza 503 si el motor de búsqueda no está disponible."""
    if not search_engine:
        raise HTTPException(status_code=503, detail="Motor de búsqueda no disponible")


async def get_current_user(authorization: str = Header(default=None)) -> Optional[Dict]:
    """Dependency: extrae usuario del token JWT. Devuelve None si no hay token."""
    if not authorization:
        return None
    try:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return None
        return auth_system.verify_access_token(token)
    except Exception:
        return None


def require_auth(current_user: Optional[Dict] = Depends(get_current_user)) -> Dict:
    """Dependency: exige autenticación JWT válida."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Token de autenticación requerido")
    return current_user


def calculate_compatibility_score(result: Dict, profile: Dict) -> float:
    """Calcula un score de compatibilidad entre un resultado y el perfil del usuario."""
    score = result.get("relevance_score", 0) * 0.4

    if profile.get("interests") and result.get("categorias"):
        interests_lower = profile["interests"].lower()
        categorias_lower = result["categorias"].lower()
        if any(word in categorias_lower for word in interests_lower.split() if len(word) > 3):
            score += 0.3

    if profile.get("preferred_areas") and result.get("categorias"):
        areas_lower = profile["preferred_areas"].lower()
        categorias_lower = result["categorias"].lower()
        if any(word in categorias_lower for word in areas_lower.split() if len(word) > 3):
            score += 0.2

    if result.get("if_sjr"):
        try:
            score += min(float(result["if_sjr"]) / 10.0, 0.1)
        except (ValueError, TypeError):
            pass

    return min(score, 1.0)


# ========== RUTAS FRONTEND ==========

@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
async def read_root():
    """Servir la página principal del frontend."""
    if os.path.exists("frontend/index.html"):
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Frontend no encontrado</h1>")


# ========== AUTENTICACIÓN ==========

@app.post("/api/auth/register", tags=["Autenticación"])
async def register(request: RegisterRequest):
    """Registrar un nuevo usuario."""
    try:
        valid, msg = auth_system.validate_password(request.password)
        if not valid:
            raise HTTPException(status_code=400, detail=msg)
        if not auth_system.validate_email(request.email):
            raise HTTPException(status_code=400, detail="Email inválido")

        result = auth_system.register(request.username, request.email, request.password)
        if result["success"]:
            return {"success": True, "user_id": result["user_id"], "username": result["username"]}
        raise HTTPException(status_code=400, detail=result.get("message", "Error en registro"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error en registro: %s", e)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@app.post("/api/auth/login", tags=["Autenticación"])
async def login(request: LoginRequest):
    """Iniciar sesión."""
    try:
        result = auth_system.login(request.username, request.password)
        if result["success"]:
            return {"success": True, "token": result["token"], "user": result["user"]}
        raise HTTPException(status_code=401, detail=result.get("message", "Credenciales inválidas"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error en login: %s", e)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# ========== PERFIL ==========

@app.get("/api/profile/{user_id}", tags=["Perfiles"])
async def get_profile(user_id: int):
    """Obtener el perfil de un usuario."""
    try:
        profile = auth_system.get_profile(user_id)
        if profile:
            return profile
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo perfil: %s", e)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@app.put("/api/profile/{user_id}", tags=["Perfiles"])
async def update_profile(user_id: int, profile_data: ProfileUpdate):
    """Actualizar el perfil de un usuario."""
    try:
        data = profile_data.model_dump(exclude_unset=True)
        result = auth_system.update_profile(user_id, data)
        if result["success"]:
            return {"success": True, "message": result["message"]}
        raise HTTPException(status_code=400, detail=result.get("message", "Error al actualizar"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error actualizando perfil: %s", e)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# ========== BÚSQUEDA ==========

@app.get("/api/stats", tags=["Búsqueda"])
async def get_stats():
    """Obtener estadísticas globales de la base de datos."""
    _require_search_engine()
    try:
        return search_engine.get_database_stats()
    except Exception as e:
        logger.error("Error obteniendo stats: %s", e)
        raise HTTPException(status_code=500, detail="Error obteniendo estadísticas")


@app.post("/api/search", tags=["Búsqueda"])
async def search(request: SearchRequest):
    """Buscar en la base de datos por query y filtros."""
    _require_search_engine()
    try:
        return search_engine.search(
            query=request.query,
            limit=request.limit,
            filters=request.filters,
        )
    except Exception as e:
        logger.error("Error en búsqueda: %s", e)
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {str(e)}")


@app.get("/api/professor/{professor_name}", tags=["Búsqueda"])
async def get_professor(professor_name: str):
    """Obtener el perfil completo de un profesor."""
    _require_search_engine()
    try:
        profile = search_engine.get_profesor_profile(professor_name)
        if profile:
            return profile
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo profesor: %s", e)
        raise HTTPException(status_code=500, detail="Error obteniendo perfil del profesor")


@app.get("/api/production-types", tags=["Búsqueda"])
async def get_production_types():
    """Obtener lista de tipos de producción disponibles."""
    _require_search_engine()
    try:
        stats = search_engine.get_database_stats()
        return list(stats.get("tipos_produccion", {}).keys())
    except Exception as e:
        logger.error("Error obteniendo tipos: %s", e)
        return []


# ========== RECOMENDACIONES ==========

@app.get("/api/recommendations/{user_id}", tags=["Recomendaciones"])
async def get_recommendations(user_id: int, limit: int = Query(default=10, ge=1, le=50)):
    """Obtener recomendaciones personalizadas basadas en el perfil del usuario."""
    _require_search_engine()
    try:
        profile = auth_system.get_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Perfil no encontrado")

        query_parts = [
            profile.get("interests", ""),
            profile.get("preferred_areas", ""),
            profile.get("skills", ""),
        ]
        query_parts = [p for p in query_parts if p]

        if not query_parts:
            return {
                "query": "",
                "total_results": 0,
                "results": [],
                "message": "Completa tu perfil para obtener recomendaciones personalizadas",
            }

        recommendation_query = ", ".join(query_parts)
        results = search_engine.search(query=recommendation_query, limit=limit)

        for result in results.get("results", []):
            result["compatibility_score"] = calculate_compatibility_score(result, profile)

        results["results"].sort(key=lambda x: x.get("compatibility_score", 0), reverse=True)
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generando recomendaciones: %s", e)
        raise HTTPException(status_code=500, detail="Error generando recomendaciones")


# ========== CHAT IA (RAG Avanzado) ==========

def _detect_professor_name(message: str) -> Optional[str]:
    """Detecta si el mensaje del usuario menciona un profesor de la BD."""
    if not search_engine:
        return None
    try:
        professors = search_engine.get_all_professor_names()
        message_lower = message.lower()
        for name in professors:
            if name.lower() in message_lower:
                return name
        # Búsqueda parcial por apellido (mínimo 2 palabras)
        for name in professors:
            parts = name.lower().split()
            if len(parts) >= 2 and any(p in message_lower for p in parts if len(p) > 3):
                matches = sum(1 for p in parts if p in message_lower)
                if matches >= 2:
                    return name
    except Exception:
        pass
    return None


@app.post("/api/chat", tags=["IA Asistente"])
async def chat(request: ChatMessage):
    """
    Chat clásico (no streaming) con el asistente IA.

    Se mantiene por compatibilidad, aunque el frontend moderno usará
    la ruta /api/chat/stream para obtener la respuesta de forma progresiva.
    """
    if not llm:
        raise HTTPException(
            status_code=503,
            detail="Servicio de IA no disponible. Verifica tu API key en .env",
        )

    try:
        profile = auth_system.get_profile(request.user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        detected_professor = _detect_professor_name(request.message)
        rag_documents = []
        if detected_professor and search_engine:
            rag_documents = search_engine.get_professor_documents(
                detected_professor, limit=15
            )
            logger.info(
                "RAG: Detectado profesor '%s', inyectando %d documentos",
                detected_professor,
                len(rag_documents),
            )

        context = _build_chat_context(
            profile,
            rag_documents,
            detected_professor,
            last_feedback_positive=request.last_feedback_positive,
        )

        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        messages = [SystemMessage(content=context)]

        if request.chat_history:
            for msg in request.chat_history:
                if msg.get("type") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("type") == "assistant":
                    messages.append(AIMessage(content=msg.get("content", "")))

        messages.append(HumanMessage(content=request.message))

        logger.info("Generando respuesta IA (modo clásico) para usuario %d", request.user_id)
        response = llm.invoke(messages)

        if not response or not hasattr(response, "content"):
            raise Exception("Respuesta inválida del modelo")

        return {
            "response": response.content,
            "rag_professor": detected_professor,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error en chat: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error generando respuesta: {str(e)}"
        )


@app.post("/api/chat/stream", tags=["IA Asistente"])
async def chat_stream(payload: ChatMessage, fastapi_request: Request):
    """
    Chat en modo streaming, enviando la respuesta token a token.

    El frontend consumirá este endpoint con fetch y un ReadableStream,
    permitiendo simular el efecto "typing" y poder interrumpir la generación.
    """
    from fastapi import Request as FastAPIRequest  # type: ignore

    if not llm:
        raise HTTPException(
            status_code=503,
            detail="Servicio de IA no disponible. Verifica tu API key en .env",
        )

    try:
        profile = auth_system.get_profile(payload.user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        detected_professor = _detect_professor_name(payload.message)
        rag_documents = []
        if detected_professor and search_engine:
            rag_documents = search_engine.get_professor_documents(
                detected_professor, limit=15
            )
            logger.info(
                "RAG (stream): Detectado profesor '%s', inyectando %d documentos",
                detected_professor,
                len(rag_documents),
            )

        context = _build_chat_context(profile, rag_documents, detected_professor)

        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        messages = [SystemMessage(content=context)]

        if payload.chat_history:
            for msg in payload.chat_history:
                if msg.get("type") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("type") == "assistant":
                    messages.append(AIMessage(content=msg.get("content", "")))

        messages.append(HumanMessage(content=payload.message))

        logger.info("Generando respuesta IA (streaming) para usuario %d", payload.user_id)

        async def token_generator():
            """
            Generador asíncrono que envía trozos de texto al cliente.

            Si el cliente cierra la conexión (por ej. botón "Stop"), se interrumpe el bucle.
            """
            try:
                # astream devuelve un async iterator de chunks (ChatGenerationChunk)
                async for chunk in llm.astream(messages):
                    # Si el cliente ha cerrado la conexión, cortamos.
                    if await fastapi_request.is_disconnected():
                        logger.info("Cliente desconectado, cancelando streaming de chat.")
                        break

                    content = getattr(chunk, "content", None)
                    if not content:
                        continue

                    # Enviamos texto plano; el frontend se encarga del renderizado progresivo.
                    yield content
            except Exception as e:
                logger.error("Error en streaming de chat: %s", e, exc_info=True)
                # Enviamos un mensaje de error legible al usuario.
                yield "\n[Error generando respuesta IA]"

        return StreamingResponse(token_generator(), media_type="text/plain")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error en chat (stream): %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error generando respuesta (stream): {str(e)}"
        )


def _build_chat_context(
    profile: Dict,
    rag_documents: Optional[List[str]] = None,
    detected_professor: Optional[str] = None,
    last_feedback_positive: Optional[bool] = None,
) -> str:
    """Construye el prompt de sistema con RAG opcional."""
    context = """Eres un asistente inteligente especializado en ayudar a estudiantes universitarios a encontrar tema y tutor para su Trabajo de Fin de Grado (TFG).

Tu objetivo:
1. Recomendar áreas de investigación y tipos de tutores adecuados
2. Sugerir ideas de proyectos TFG relevantes y actuales
3. Proporcionar información sobre profesores y sus áreas de investigación
4. Ayudar al estudiante a tomar decisiones informadas

"""
    context += "=== INFORMACIÓN DEL ESTUDIANTE ===\n"
    context += f"Usuario: {profile.get('username')}\n"

    for key, label in [
        ("full_name", "Nombre"),
        ("degree", "Grado/Carrera"),
        ("year", "Año académico"),
    ]:
        if profile.get(key):
            context += f"{label}: {profile[key]}\n"

    context += "\n"

    for key, emoji, label in [
        ("interests", "🎯", "INTERESES"),
        ("skills", "💻", "HABILIDADES"),
        ("preferred_areas", "📚", "ÁREAS PREFERIDAS"),
    ]:
        if profile.get(key):
            context += f"{emoji} {label}: {profile[key]}\n"

    # RAG: inyectar documentos del profesor
    if rag_documents and detected_professor:
        context += f"\n=== PUBLICACIONES DE {detected_professor.upper()} ===\n"
        context += "El estudiante ha preguntado sobre este profesor. Usa sus publicaciones reales para responder:\n\n"
        for i, doc in enumerate(rag_documents[:10], 1):
            context += f"{i}. {doc[:300]}\n\n"
        context += "INSTRUCCIÓN ESPECIAL: Puedes mencionar a este profesor por nombre ya que el alumno preguntó directamente. Basa tu respuesta en sus publicaciones reales.\n"
    else:
        # Modo general: usar estadísticas de la DB
        if search_engine:
            try:
                stats = search_engine.get_database_stats()
                context += f"\n=== BASE DE DATOS ===\n"
                context += f"Acceso a {stats.get('total_profesores', 0)} profesores y {stats.get('total_documents', 0)} trabajos.\n"
                if stats.get("categorias_populares"):
                    top = list(stats["categorias_populares"].keys())[:5]
                    context += f"Áreas principales: {', '.join(top)}\n"
            except Exception:
                pass
        context += "\nIMPORTANTE: NO recomiendes profesores por nombre. Sugiere áreas y tipos de tutores.\n"

    if last_feedback_positive is True:
        context += "\n=== FEEDBACK DEL USUARIO ===\n"
        context += "El usuario indicó que la última recomendación le fue útil. Mantén un estilo y enfoque similar.\n"
    elif last_feedback_positive is False:
        context += "\n=== FEEDBACK DEL USUARIO ===\n"
        context += "El usuario indicó que la última recomendación no le fue útil. Adapta tu enfoque y propón alternativas diferentes.\n"

    context += """\n=== INSTRUCCIONES ===
- Responde de forma concisa (3-6 líneas)
- Usa SIEMPRE la información del perfil en tus recomendaciones
- Si el perfil está incompleto, sugiere completarlo
- Da respuestas concretas y prácticas
- Estructura la respuesta en párrafos cortos y, cuando tenga sentido, usa listas con guiones.
"""
    return context


# ========== EXPORTACIÓN ==========

@app.post("/api/export/csv", tags=["Exportación"])
async def export_csv(request: SearchRequest):
    """Exportar resultados de búsqueda a formato CSV."""
    _require_search_engine()
    try:
        results = search_engine.search(
            query=request.query, limit=request.limit, filters=request.filters
        )

        data = [
            {
                "Título": res.get("titulo", ""),
                "Profesor": res.get("profesor", ""),
                "Fecha": res.get("fecha", ""),
                "Tipo Producción": res.get("tipo_produccion", ""),
                "Categorías": res.get("categorias", ""),
                "IF SJR": res.get("if_sjr", ""),
                "Cuartil SJR": res.get("q_sjr", ""),
                "Relevancia": res.get("relevance_score", 0),
                "Fuente": res.get("fuente", ""),
            }
            for res in results.get("results", [])
        ]

        df = pd.DataFrame(data)
        output = io.StringIO()
        df.to_csv(output, index=False, encoding="utf-8-sig")
        output.seek(0)

        filename = f"resultados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.error("Error exportando CSV: %s", e)
        raise HTTPException(status_code=500, detail="Error exportando resultados")


# ========== HISTORIAL ==========

@app.get("/api/history/{user_id}", tags=["Historial"])
async def get_history(user_id: int, limit: int = Query(default=10, ge=1, le=100)):
    """Obtener historial de búsquedas de un usuario."""
    try:
        return auth_system.get_search_history(user_id, limit)
    except Exception as e:
        logger.error("Error obteniendo historial: %s", e)
        raise HTTPException(status_code=500, detail="Error obteniendo historial")


@app.delete("/api/history/{user_id}", tags=["Historial"])
async def clear_history(user_id: int):
    """Eliminar el historial de búsquedas de un usuario."""
    try:
        result = auth_system.clear_search_history(user_id)
        if result["success"]:
            return {"success": True}
        raise HTTPException(status_code=400, detail=result.get("message"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error eliminando historial: %s", e)
        raise HTTPException(status_code=500, detail="Error eliminando historial")


@app.post("/api/history/{user_id}", tags=["Historial"])
async def add_history(user_id: int, request: HistoryRequest):
    """Agregar una búsqueda al historial."""
    try:
        auth_system.add_search_history(user_id, request.query, request.search_type)
        return {"success": True}
    except Exception as e:
        logger.error("Error agregando historial: %s", e)
        return {"success": False, "error": str(e)}


# ========== ANÁLISIS DE PROFESOR (IA) ==========

@app.get("/api/professor/{professor_name}/analysis", tags=["IA Asistente"])
async def professor_analysis(professor_name: str):
    """Análisis de estilo y tono de un profesor usando IA."""
    _require_search_engine()
    if not llm:
        raise HTTPException(status_code=503, detail="Servicio de IA no disponible")

    try:
        docs = search_engine.get_professor_documents(professor_name, limit=20)
        if not docs:
            raise HTTPException(status_code=404, detail="Profesor no encontrado")

        from langchain_core.messages import SystemMessage, HumanMessage

        prompt = f"""Analiza el estilo y perfil investigador del profesor {professor_name} basándote en sus publicaciones.

PUBLICACIONES:
"""
        for i, doc in enumerate(docs[:15], 1):
            prompt += f"{i}. {doc[:250]}\n"

        prompt += """
Responde en formato JSON con esta estructura exacta:
{{
  "estilo_predominante": "técnico" | "divulgativo" | "teórico" | "práctico",
  "areas_principales": ["area1", "area2", "area3"],
  "nivel_productividad": "alto" | "medio" | "bajo",
  "perfil_resumen": "Breve descripción de 2-3 frases del perfil investigador",
  "tipo_tfg_recomendado": "Qué tipo de TFG encajaría con este profesor",
  "fortalezas": ["fortaleza1", "fortaleza2"]
}}"""

        messages = [
            SystemMessage(content="Eres un analista académico. Responde SOLO con JSON válido."),
            HumanMessage(content=prompt),
        ]

        response = llm.invoke(messages)
        # Intentar parsear JSON de la respuesta
        import json
        try:
            # Limpiar posible markdown
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            analysis = json.loads(content)
        except json.JSONDecodeError:
            analysis = {"perfil_resumen": response.content}

        analysis["profesor"] = professor_name
        analysis["total_publicaciones"] = len(docs)
        return analysis

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error en análisis de profesor: %s", e)
        raise HTTPException(status_code=500, detail="Error generando análisis")


# ========== GENERADOR DE IDEAS TFG ==========

@app.get("/api/generate-ideas/{user_id}", tags=["IA Asistente"])
async def generate_ideas(user_id: int):
    """Genera 3 ideas de TFG personalizadas basadas en el perfil del usuario."""
    _require_search_engine()
    if not llm:
        raise HTTPException(status_code=503, detail="Servicio de IA no disponible")

    try:
        profile = auth_system.get_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Perfil no encontrado")

        # Buscar publicaciones afines al perfil
        query_parts = [
            profile.get("interests", ""),
            profile.get("preferred_areas", ""),
            profile.get("skills", ""),
        ]
        query = ", ".join(p for p in query_parts if p)
        if not query:
            return {
                "ideas": [],
                "message": "Completa tu perfil (intereses, áreas) para generar ideas personalizadas",
            }

        results = search_engine.search(query=query, limit=15)

        from langchain_core.messages import SystemMessage, HumanMessage

        prompt = f"""Genera 3 ideas de Trabajo de Fin de Grado (TFG) personalizadas.

PERFIL DEL ESTUDIANTE:
- Grado: {profile.get('degree', 'No especificado')}
- Intereses: {profile.get('interests', 'No especificado')}
- Habilidades: {profile.get('skills', 'No especificado')}
- Áreas preferidas: {profile.get('preferred_areas', 'No especificado')}

PUBLICACIONES RELEVANTES ENCONTRADAS EN LA BD:
"""
        for r in results.get("results", [])[:10]:
            prompt += f"- {r.get('titulo', '')} ({r.get('categorias', '')}) — {r.get('profesor', '')}\n"

        prompt += """

Responde en formato JSON con esta estructura exacta:
{{
  "ideas": [
    {{
      "titulo": "Título del TFG",
      "descripcion": "Descripción de 2-3 frases",
      "area": "Área de investigación",
      "tecnologias": ["tech1", "tech2"],
      "dificultad": "media" | "alta"
    }}
  ]
}}"""

        messages = [
            SystemMessage(content="Eres un asesor académico experto en TFGs. Responde SOLO con JSON válido."),
            HumanMessage(content=prompt),
        ]

        response = llm.invoke(messages)
        import json
        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            ideas = json.loads(content)
        except json.JSONDecodeError:
            ideas = {"ideas": [], "raw_response": response.content}

        return ideas

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generando ideas: %s", e)
        raise HTTPException(status_code=500, detail="Error generando ideas de TFG")


# ========== RANKING DE DISPONIBILIDAD ==========

@app.get("/api/professors/ranking", tags=["Búsqueda"])
async def professors_ranking():
    """Obtener ranking de disponibilidad estimada de profesores."""
    _require_search_engine()
    try:
        return search_engine.get_availability_ranking()
    except Exception as e:
        logger.error("Error obteniendo ranking: %s", e)
        raise HTTPException(status_code=500, detail="Error obteniendo ranking")


# ========== HEALTH CHECK ==========

@app.get("/api/health", tags=["Sistema"])
async def health_check():
    """Verificar el estado de todos los componentes del sistema."""
    return {
        "status": "ok",
        "version": "3.0.0",
        "components": {
            "search_engine": search_engine is not None,
            "llm": llm is not None,
            "auth_system": auth_system is not None,
        },
    }


# ========== PUNTO DE ENTRADA ==========

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
