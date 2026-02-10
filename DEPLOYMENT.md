# 🚀 Guía de Despliegue — TFG Scraper Pro v3.0

## Opción A: Docker (Recomendado)
Ideal para desplegar en otros ordenadores o servidores.
1. Instalar Docker Desktop.
2. Crear archivo `.env` con `OPENROUTER_API_KEY`.
3. Ejecutar: `docker-compose up --build -d`.
4. Acceder en `http://localhost:8000`.

## Opción B: Manual (Python)
1. Crear venv: `python -m venv venv`.
2. Activar: `.\venv\Scripts\activate`.
3. Instalar: `pip install -r requirements.txt`.
4. Ejecutar: `python app.py`.

## GitHub Actions (CI/CD)
Cada vez que hagas `git push`, GitHub ejecutará automáticamente los tests en la nube para asegurar que el código es estable.
