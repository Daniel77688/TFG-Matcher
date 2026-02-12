# 📦 Instalación y Despliegue — TFG Scraper Pro

Guía completa para instalar, configurar y ejecutar TFG Scraper Pro en entorno local o con Docker.

---

## Requisitos previos

| Requisito | Versión mínima |
|-----------|----------------|
| Python | 3.10+ |
| pip | 22.0+ |
| (Opcional) Docker | 20.10+ |
| (Opcional) Docker Compose | 2.0+ |

---

## Instalación local

### 1. Clonar el repositorio

```bash
git clone https://github.com/Daniel77688/TFG-Matcher.git
cd TFG-Matcher
```

### 2. Crear entorno virtual (recomendado)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

> **Nota:** La primera instalación puede tardar varios minutos debido a `sentence-transformers` y `chromadb`.

### 4. Configurar variables de entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
# Obligatorio para el asistente IA
OPENROUTER_API_KEY=tu_api_key_aqui

# Opcional: modelo de IA (por defecto: xiaomi/mimo-v2-flash:free)
MODEL_NAME=xiaomi/mimo-v2-flash:free

# Opcional: JWT (cambiar en producción)
JWT_SECRET_KEY=tfg-scraper-secret-change-in-production
JWT_EXPIRE_HOURS=24
```

Para obtener una API key de OpenRouter: https://openrouter.ai/keys

### 5. Cargar datos en ChromaDB

Antes de ejecutar la aplicación, es necesario cargar las publicaciones en la base de datos vectorial:

```bash
python -m src.data.data_loader
```

- Lee CSVs de `data/csv/` y, si está vacío, de `frontend/static/data/`
- Genera embeddings con SentenceTransformers
- Crea la colección `profesores_tfg` en `chroma_db/`

Salida esperada:

```
✅ Datos cargados correctamente
Total documentos en colección: 6
```

### 6. Ejecutar la aplicación

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

O con el script incluido (si existe):

```bash
python app.py
```

Abrir en el navegador: **http://localhost:8000**

---

## Instalación con Docker

### Opción A: Docker Compose (recomendado)

#### 1. Crear `.env`

```env
OPENROUTER_API_KEY=tu_api_key_aqui
MODEL_NAME=xiaomi/mimo-v2-flash:free
```

#### 2. Cargar datos antes del primer arranque

Los volúmenes de Docker se crean al iniciar. Para que ChromaDB tenga datos:

**Opción 2a — Cargar datos localmente antes de Docker**

```bash
# Instalar dependencias localmente
pip install -r requirements.txt

# Cargar datos (creará chroma_db/ y data/)
python -m src.data.data_loader

# Luego arrancar Docker
docker-compose up --build
```

**Opción 2b — Entrar al contenedor y cargar**

```bash
docker-compose up -d
docker-compose exec web python -m src.data.data_loader
```

#### 3. Ejecutar

```bash
docker-compose up --build
```

La aplicación estará en **http://localhost:8000**

#### 4. Detener

```bash
docker-compose down
```

### Opción B: Solo Docker (sin Compose)

```bash
# Construir imagen
docker build -t tfg-scraper .

# Crear directorios para persistencia
mkdir -p chroma_db data

# Cargar datos (ejecutar data_loader localmente primero o montar data/)
python -m src.data.data_loader

# Ejecutar contenedor
docker run -p 8000:8000 \
  -v $(pwd)/chroma_db:/app/chroma_db \
  -v $(pwd)/users.db:/app/users.db \
  -v $(pwd)/data:/app/data \
  -e OPENROUTER_API_KEY=tu_api_key \
  tfg-scraper
```

---

## Estructura de volúmenes (Docker)

| Volumen | Descripción |
|---------|-------------|
| `./chroma_db` | Base de datos vectorial (embeddings) |
| `./users.db` | Base de datos SQLite de usuarios |
| `./data` | Directorio con CSVs de profesores |

---

## Directorios del proyecto

```
TFG-Matcher/
├── app.py                 # Punto de entrada FastAPI
├── requirements.txt       # Dependencias Python
├── .env                   # Variables de entorno (crear)
├── Dockerfile
├── docker-compose.yml
│
├── data/csv/              # CSVs de profesores (opcional)
├── chroma_db/             # ChromaDB (se crea al cargar datos)
├── users.db               # SQLite usuarios (se crea al registrar)
│
├── frontend/              # Frontend SPA
│   ├── index.html
│   └── static/
│       ├── style.css
│       ├── data/          # CSVs demo
│       └── js/
│
├── src/                   # Código fuente
│   ├── auth/              # Autenticación
│   ├── config/            # Configuración
│   ├── data/              # Procesamiento de datos
│   ├── search/            # Motor de búsqueda
│   └── utils/             # Utilidades
│
└── scripts/               # Scripts auxiliares
    └── script_descargar_datos.py
```

---

## Solución de problemas

### "Motor de búsqueda no disponible"

- Ejecutar `python -m src.data.data_loader` para crear ChromaDB.
- Comprobar que existe `chroma_db/` con la colección.

### "Servicio de IA no disponible"

- Comprobar que `OPENROUTER_API_KEY` está definida en `.env`.
- Verificar que la API key es válida en https://openrouter.ai/

### Error al instalar sentence-transformers

- En macOS ARM (M1/M2): asegurar `pip` actualizado y usar Python 3.10+.
- En Linux: instalar `build-essential` si hay errores de compilación.

### Puerto 8000 en uso

```bash
uvicorn app:app --host 0.0.0.0 --port 8080
```

---

## Tests

```bash
python -m pytest tests/ -v
```

---

## Documentación API

Una vez ejecutada la aplicación:

- **Swagger UI:** http://localhost:8000/docs  
- **ReDoc:** http://localhost:8000/redoc  
