# 📚 DOCUMENTATION — TFG Scraper Pro

Documentación completa del sistema de recomendación de tutores TFG para la URJC.

---

## 📋 Descripción del Proyecto

**TFG Scraper Pro** es un sistema inteligente que ayuda a estudiantes universitarios de la URJC a encontrar el tutor ideal para su Trabajo de Fin de Grado (TFG). Combina **búsqueda semántica** sobre publicaciones académicas con un **asistente IA** personalizado.

### Funcionalidades principales

| Funcionalidad | Descripción |
|---|---|
| 🔍 **Búsqueda Semántica** | Búsqueda por tema o palabras clave con filtros (tipo, cuartil, IF) |
| 👨‍🏫 **Perfiles de Profesores** | Vista detallada de cada profesor con estadísticas y trabajos |
| 📊 **Comparación** | Comparación lado a lado entre dos profesores |
| 🤖 **Asistente IA** | Chat con IA que conoce tu perfil y la base de datos |
| 💡 **Recomendaciones** | Sugerencias automáticas basadas en tu perfil académico |
| 📥 **Exportación CSV** | Descarga de resultados de búsqueda |
| 📜 **Historial** | Registro de todas tus búsquedas |

---

## 🏗️ Arquitectura del Sistema

```
┌────────────────────────────────────────────┐
│              Frontend (HTML/JS)            │
│    index.html + módulos JS + style.css     │
└──────────────────┬─────────────────────────┘
                   │ HTTP/REST
┌──────────────────▼─────────────────────────┐
│            Backend (FastAPI)               │
│               app.py                       │
├────────────┬──────────┬────────────────────┤
│ AuthSystem │ SearchEng│ LLM (OpenRouter)   │
│ (SQLite)   │ (Chroma) │ (LangChain)        │
└────────────┴──────────┴────────────────────┘
```

---

## 📁 Estructura del Proyecto

```
TFG_Scraper/
├── app.py                          # Backend FastAPI (punto de entrada)
├── requirements.txt                # Dependencias del proyecto
├── .env                            # Variables de entorno (API keys)
├── .gitignore
│
├── src/                            # Código fuente principal
│   ├── auth/
│   │   ├── auth.py                 # Sistema de autenticación (SQLModel)
│   │   └── auth_interface.py       # Interfaz CLI (legacy)
│   ├── config/
│   │   └── config.py               # Configuración centralizada
│   ├── data/
│   │   ├── data_processor_pandas.py # Procesamiento de CSVs + embeddings
│   │   └── data_loader.py          # Script de carga de datos
│   ├── search/
│   │   └── search_engine.py        # Motor de búsqueda semántica
│   └── utils/
│       └── text_utils.py           # Normalización de texto
│
├── frontend/                       # Frontend web
│   ├── index.html                  # Página principal (SPA)
│   └── static/
│       ├── style.css               # Estilos
│       └── js/                     # JavaScript modular
│           ├── main.js             # Orquestador principal
│           ├── api.js              # Cliente HTTP
│           ├── auth.js             # Lógica de autenticación
│           ├── chat.js             # Chat con IA
│           ├── search.js           # Lógica de búsqueda
│           ├── state.js            # Estado global
│           └── ui.js               # Utilidades de UI
│
├── tests/                          # Tests automatizados (pytest)
│   ├── conftest.py                 # Fixtures reutilizables
│   ├── test_api.py                 # Tests de la API
│   └── test_normalization.py       # Tests de normalización
│
├── scripts/
│   └── script_descargar_datos.py   # Web scraper de datos (Selenium)
│
├── data/csv/                       # Archivos CSV de profesores
└── chroma_db/                      # Base de datos vectorial
```

---

## 🔌 API Endpoints

Base URL: `http://localhost:8000/api`

### Autenticación

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/auth/register` | Registrar usuario (username, email, password) |
| `POST` | `/auth/login` | Iniciar sesión |

### Perfiles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/profile/{user_id}` | Obtener perfil de usuario |
| `PUT` | `/profile/{user_id}` | Actualizar perfil (nombre, grado, intereses...) |

### Búsqueda

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/search` | Búsqueda semántica con filtros |
| `GET` | `/professor/{name}` | Perfil completo de un profesor |
| `GET` | `/stats` | Estadísticas globales de la base de datos |
| `GET` | `/production-types` | Lista de tipos de producción |
| `GET` | `/recommendations/{user_id}` | Recomendaciones personalizadas |

### Chat IA

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/chat` | Enviar mensaje al asistente IA |

### Historial y Exportación

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/history/{user_id}` | Obtener historial de búsquedas |
| `POST` | `/history/{user_id}` | Agregar entrada al historial |
| `DELETE` | `/history/{user_id}` | Eliminar historial |
| `POST` | `/export/csv` | Exportar resultados a CSV |

### Sistema

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/health` | Health check del sistema |

> 📄 Documentación interactiva disponible en `http://localhost:8000/docs` (Swagger UI)

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|---|---|
| **Backend** | FastAPI, Uvicorn |
| **Base de Datos Usuarios** | SQLite + SQLModel |
| **Base de Datos Vectorial** | ChromaDB |
| **Embeddings** | SentenceTransformers (all-MiniLM-L6-v2) |
| **IA / Chat** | LangChain + OpenRouter (GPT-4o-mini) |
| **Frontend** | HTML5, CSS3, JavaScript (ES Modules) |
| **Scraping** | Selenium + BeautifulSoup4 |
| **Testing** | Pytest + FastAPI TestClient |

---

## 🚀 Instalación y Uso

### Requisitos
- Python 3.10+
- API key de OpenRouter (para el asistente IA)

### Instalación

```bash
# 1. Clonar
git clone https://github.com/Daniel77688/TFG-Matcher.git
cd TFG-Matcher

# 2. Entorno virtual
python -m venv venv
venv\Scripts\activate     # Windows
source venv/bin/activate  # macOS/Linux

# 3. Dependencias
pip install -r requirements.txt

# 4. Variables de entorno
# Crear .env con:
# OPENROUTER_API_KEY=tu_api_key
# MODEL_NAME=xiaomi/mimo-v2-flash:free
```

### Carga de datos

```bash
python -m src.data.data_loader
```

### Ejecutar

```bash
python app.py
# Abrir http://localhost:8000
```

### Tests

```bash
python -m pytest tests/ -v
```

---

## 🔐 Seguridad

- Contraseñas hasheadas con **bcrypt**
- Validación de email con regex
- Validación de contraseña (mín. 8 caracteres, mayúscula, minúscula, número)
- Sesión almacenada en `localStorage` (cliente)
- CORS configurado (ajustar en producción)

---

## 📈 Mejoras Técnicas v2.1

- **Caché de estadísticas** — TTL de 5 minutos para `get_database_stats()`
- **Logging profesional** — Timestamps y niveles en toda la aplicación
- **Pydantic v2** — Uso de `.model_dump()` en vez del deprecado `.dict()`
- **OpenAPI tags** — Endpoints categorizados en la documentación Swagger
- **Query validation** — Límites validados con `ge`/`le` en parámetros
- **Frontend accesible** — ARIA labels, roles, screen reader support
- **SEO** — Meta tags, OG tags, favicon
- **Tests profesionales** — Pytest con fixtures, parametrización y 16+ test cases
