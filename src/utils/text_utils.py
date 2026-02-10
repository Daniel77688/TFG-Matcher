import unicodedata
import re

def normalize_text(text: str) -> str:
    """
    Normaliza el texto para búsquedas y procesamiento de datos:
    - Convierte a minúsculas
    - Elimina acentos/tildes
    - Elimina espacios extra
    - Elimina caracteres especiales raros manteniendo alfanuméricos y básicos
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Convertir a minúsculas
    text = text.lower()
    
    # Eliminar acentos/tildes usando NFKD y filtrando caracteres no-espaciados
    text = unicodedata.normalize('NFKD', text)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    
    # Eliminar caracteres raros (mantener solo letras, números y espacios básicos)
    # También permitimos puntos y comas si son parte de una estructura, 
    # pero para normalización pura a veces es mejor quitarlos o limpiarlos.
    # Aquí nos enfocamos en limpiar "caracteres raros"
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Colapsar múltiples espacios y strip
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def generate_username(name: str) -> str:
    """Genera un username normalizado a partir de un nombre"""
    normalized = normalize_text(name)
    return normalized.replace(" ", ".")
