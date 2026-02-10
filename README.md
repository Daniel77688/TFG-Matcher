# 🎓 TFG Scraper Pro

Sistema inteligente de recomendación de tutores TFG para la **URJC**. Combina búsqueda semántica sobre publicaciones académicas con un asistente IA personalizado.

## ✨ Características

- 🔍 **Búsqueda semántica** — Encuentra tutores por tema, palabra clave o filtros
- 🤖 **Asistente IA** — Chat personalizado que conoce tu perfil académico
- 📊 **Comparación** — Compara perfiles de profesores lado a lado
- 💡 **Recomendaciones** — Sugerencias automáticas basadas en tus intereses
- 👤 **Perfiles** — Gestión de perfil de estudiante con intereses y habilidades
- 📥 **Exportación** — Descarga resultados de búsqueda en CSV

## 🚀 Inicio Rápido

```bash
# Instalar dependencias
pip install -r requirements.txt

# Cargar datos en ChromaDB
python -m src.data.data_loader

# Ejecutar la aplicación
python app.py
# → http://localhost:8000
```

## 🔧 Configuración

Crear archivo `.env` en la raíz:

```env
OPENROUTER_API_KEY=tu_api_key_aqui
MODEL_NAME=xiaomi/mimo-v2-flash:free
```

## 🧪 Tests

```bash
python -m pytest tests/ -v
```

## 📚 Documentación

Ver [DOCUMENTATION.md](DOCUMENTATION.md) para documentación completa: arquitectura, API endpoints, stack tecnológico, y más.

## 🛠️ Tech Stack

| | Tecnología |
|---|---|
| Backend | FastAPI + Uvicorn |
| DB Usuarios | SQLite + SQLModel |
| DB Vectorial | ChromaDB |
| Embeddings | SentenceTransformers |
| IA | LangChain + OpenRouter |
| Frontend | HTML5, CSS3, JS (ES Modules) |
| Tests | Pytest |

---

Desarrollado como Trabajo de Fin de Grado — Universidad Rey Juan Carlos
