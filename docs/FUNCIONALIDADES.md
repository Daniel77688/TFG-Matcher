# 📚 Funcionalidades y Arquitectura — TFG Scraper Pro

Documentación detallada de las funcionalidades del sistema, clases, módulos y su propósito.

---

## Visión general

**TFG Scraper Pro** es un sistema de recomendación de tutores TFG para la URJC que combina:

1. **Búsqueda semántica** sobre publicaciones académicas (ChromaDB + embeddings)
2. **Asistente IA** con contexto del perfil del estudiante y RAG
3. **Recomendaciones personalizadas** según intereses, habilidades y áreas
4. **Comparación** de profesores y **ranking de disponibilidad**

---

## Arquitectura del sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (HTML/JS)                        │
│  index.html · main.js · api.js · chat.js · search.js · …    │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/REST · JWT
┌──────────────────────────▼──────────────────────────────────┐
│                   BACKEND (FastAPI - app.py)                 │
├──────────────┬───────────────────┬──────────────────────────┤
│  AuthSystem  │   SearchEngine    │   LLM (LangChain)         │
│  SQLite      │   ChromaDB        │   OpenRouter              │
└──────────────┴───────────────────┴──────────────────────────┘
```

---

## Backend

### `app.py` — Punto de entrada

| Elemento | Descripción |
|----------|-------------|
| **create_app()** | Crea la instancia FastAPI, configura CORS y archivos estáticos |
| **Modelos Pydantic** | LoginRequest, RegisterRequest, ProfileUpdate, SearchRequest, ChatMessage, etc. |
| **Inicialización** | Carga AuthSystem, SearchEngine (ChromaDB) y LLM (OpenRouter) al arrancar |
| **Endpoints** | Agrupa las rutas en tags: Autenticación, Perfiles, Búsqueda, IA, Exportación, etc. |

Objetivo: exponer la API REST y servir el frontend.

---

### `src/config/config.py` — Configuración

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `BASE_DIR` | Raíz del proyecto | `Path(__file__).parent.parent.parent` |
| `CSV_DIR` | CSVs de profesores | `data/csv` |
| `DEMO_CSV_DIR` | CSVs demo | `frontend/static/data` |
| `CHROMA_DIR` | Base ChromaDB | `chroma_db` |
| `DB_PATH` | SQLite usuarios | `users.db` |
| `COLLECTION_NAME` | Colección ChromaDB | `profesores_tfg` |
| `EMBEDDING_MODEL` | Modelo embeddings | `all-MiniLM-L6-v2` |
| `MODEL_NAME` | Modelo IA | Env `MODEL_NAME` o `xiaomi/mimo-v2-flash:free` |
| `OPENROUTER_API_KEY` | API OpenRouter | Env |
| `JWT_SECRET_KEY` | Secreto JWT | Env |

Objetivo: centralizar rutas, modelos y credenciales.

---

### `src/auth/auth.py` — Autenticación y usuarios

#### Modelos SQLModel

| Clase | Tabla | Descripción |
|-------|-------|-------------|
| **User** | `users` | Usuario (id, username, email, password_hash, created_at, last_login) |
| **StudentProfile** | `student_profiles` | Perfil académico (degree, year, interests, skills, preferred_areas) |
| **SearchHistory** | `search_history` | Historial de búsquedas por usuario |

#### Clase `AuthSystem`

| Método | Descripción |
|--------|-------------|
| `register(username, email, password)` | Registra usuario, crea perfil vacío |
| `login(username, password)` | Login, devuelve JWT y datos del usuario |
| `validate_password(password)` | Comprueba longitud, mayúsculas, minúsculas, números |
| `validate_email(email)` | Valida formato de email |
| `create_access_token(user_id, username)` | Genera JWT con expiración |
| `verify_access_token(token)` | Valida JWT y devuelve payload |
| `get_profile(user_id)` | Obtiene perfil completo |
| `update_profile(user_id, profile_data)` | Actualiza campos permitidos del perfil |
| `add_search_history(user_id, query, search_type)` | Registra una búsqueda |
| `get_search_history(user_id, limit)` | Lista historial reciente |
| `clear_search_history(user_id)` | Borra historial |

Objetivo: gestión segura de usuarios, perfiles e historial con bcrypt y JWT.

---

### `src/data/data_processor_pandas.py` — Procesamiento de datos

#### Clase `DataProcessorPandas`

| Método | Descripción |
|--------|-------------|
| `load_all_csvs()` | Lee CSVs de `CSV_DIR` y `DEMO_CSV_DIR`, genera embeddings |
| `_process_dataframe(df, csv_path)` | Normaliza filas, mapea columnas estándar y demo (profesor, titulo, tipo_produccion, etc.) |
| `setup_chroma_collection()` | Crea o reemplaza la colección en ChromaDB |
| `load_data_to_chroma(batch_size)` | Inserta documentos y embeddings en ChromaDB por lotes |

#### Función `get_chroma_collection()`

- Devuelve la colección ChromaDB existente sin recrearla.
- Usada por el backend para inicializar el SearchEngine.

Objetivo: ingestar CSVs, generar embeddings con SentenceTransformers y poblar ChromaDB.

---

### `src/search/search_engine.py` — Motor de búsqueda

#### Clase `SearchEngine`

| Método | Descripción |
|--------|-------------|
| `search(query, limit, filters)` | Búsqueda semántica con filtros (profesor, tipo_produccion, q_sjr, min_if_sjr) |
| `_build_where_clause(filters)` | Construye cláusula WHERE para ChromaDB |
| `_process_search_results(chromaresults, filters)` | Aplica filtros post-query y normaliza resultados |
| `_passes_post_filters(metadata, filters)` | Comprueba fecha e IF mínimo |
| `get_profesor_profile(profesor_name)` | Perfil completo con estadísticas y trabajos recientes |
| `get_database_stats()` | Estadísticas globales (documentos, profesores, tipos, años, categorías) con caché TTL |
| `get_professor_documents(professor_name, limit)` | Textos de publicaciones para RAG |
| `get_all_professor_names()` | Lista de nombres de profesores |
| `get_availability_ranking()` | Ranking de disponibilidad (Alta/Media/Baja) según publicaciones recientes |
| `get_all_profesores()` | Lista de profesores con estadísticas agregadas |

Objetivo: búsqueda semántica, perfiles de profesores, estadísticas y ranking sobre ChromaDB.

---

### `src/utils/text_utils.py` — Utilidades de texto

| Función | Descripción |
|---------|-------------|
| `normalize_text(text)` | Minúsculas, sin acentos, limpia caracteres especiales, colapsa espacios |
| `generate_username(name)` | Genera username normalizado (ej. "María López" → "maria.lopez") |

Objetivo: normalización para búsquedas y metadatos.

---

## Frontend

### Módulos JavaScript

| Archivo | Descripción |
|---------|-------------|
| **main.js** | Orquestador: navegación, carga de páginas, integración con API y eventos |
| **api.js** | Cliente HTTP para todos los endpoints de la API |
| **state.js** | Estado global (currentUser, chatHistory, comparisonList, isChatStreaming) |
| **auth.js** | Login, registro, logout, verificación de token |
| **search.js** | Búsqueda por tema y por profesor, obtención de email del profesor |
| **chat.js** | Streaming de chat con `/api/chat/stream`, AbortController para Stop |
| **charts.js** | Gráficos Chart.js: publicaciones por año, categorías, radar de profesor |
| **ui.js** | Notificaciones toast, loading, escapeHtml |
| **avatars.js** | Opciones de avatar (emojis), lectura/escritura en localStorage |
| **tour.js** | Tour guiado para usuarios nuevos, persistencia en localStorage |

### Páginas / flujos

| Página | Función principal |
|--------|-------------------|
| **Auth** | Login / registro con overlay deslizante |
| **Home** | Estadísticas, gráficos, ranking de disponibilidad, acceso a recomendaciones |
| **Search** | Búsqueda por tema (filtros) y por profesor |
| **Chat** | Asistente IA en streaming + feedback "¿Te fue útil?" |
| **Compare** | Comparativa de hasta 2 profesores |
| **Recommendations** | Recomendaciones personalizadas según perfil |
| **Profile** | Edición de perfil, selector de avatar, historial |
| **History** | Listado de historial de búsquedas |

Objetivo: SPA sencilla que consume la API, gestiona estado y ofrece una interfaz coherente.

---

## Funcionalidades destacadas

### 1. Búsqueda semántica

- Consultas en lenguaje natural (ej. "Machine Learning", "ciberseguridad").
- Embeddings con `all-MiniLM-L6-v2`.
- Filtros: tipo de producción, cuartil SJR, IF mínimo.
- Búsqueda por profesor con perfil y trabajos.

### 2. Recomendaciones personalizadas

- Usa intereses, habilidades y áreas preferidas del perfil.
- `calculate_compatibility_score()` combina relevancia, coincidencias de categorías e IF.
- Resultados ordenados por puntuación de compatibilidad.

### 3. Asistente IA con RAG

- Detección de nombres de profesores en el mensaje.
- Inyección de publicaciones del profesor detectado como contexto.
- `last_feedback_positive` para adaptar el estilo según feedback anterior.
- Respuesta en streaming para mejor UX.

### 4. Feedback explícito

- Tras cada respuesta: "¿Te fue útil?" → Sí / No / Prefiero no responder.
- Si "Sí": se indica al modelo mantener un estilo similar.
- Si "No": se indica adaptar enfoque y proponer alternativas.

### 5. Ranking de disponibilidad

- Estimación según publicaciones recientes (últimos 3 años).
- Etiquetas: Alta, Media, Baja.
- Integrado en la página de Inicio.

### 6. Tour guiado

- Tour para nuevos usuarios.
- Pasos: Inicio, Búsqueda, Asistente, Comparar, Recomendaciones.
- Opción de saltar y no repetir (localStorage).

### 7. Avatares de perfil

- Selección entre 14 emojis (animales y monstruos).
- Persistencia por usuario en localStorage.
- Uso en barra superior y página de perfil.

---

## Flujo de datos

```
Usuario → Frontend (main.js) → API (api.js) → Backend (app.py)
                                    ↓
                    AuthSystem (SQLite) / SearchEngine (ChromaDB) / LLM
                                    ↓
                    Respuesta JSON / Streaming → Frontend → UI
```

---

## Dependencias principales

| Paquete | Uso |
|---------|-----|
| **FastAPI** | API REST |
| **ChromaDB** | Base vectorial y búsqueda semántica |
| **SentenceTransformers** | Embeddings |
| **LangChain + langchain-openai** | Integración con LLM vía OpenRouter |
| **SQLModel** | ORM y modelos |
| **bcrypt** | Hash de contraseñas |
| **pyjwt** | Tokens JWT |
| **pandas** | Procesamiento de CSVs |
