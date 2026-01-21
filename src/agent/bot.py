#!/usr/bin/env python3
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import sys
import os
# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config.config import MODEL_NAME, OPENROUTER_API_KEY, BASE_URL

# Configurar el modelo
llm = ChatOpenAI(
    model=MODEL_NAME,
    openai_api_key=OPENROUTER_API_KEY,
    openai_api_base=BASE_URL,
    temperature=0.7,
)

def main():
    print("=== Agente Inteligente con LangChain ===")
    print(f"Modelo actual: {MODEL_NAME}")
    print("Escribe 'salir' para terminar\n")
    
    # Historial de conversación
    mensajes = [
        SystemMessage(content="Eres un asistente útil y amigable.")
    ]
    
    while True:
        try:
            pregunta = input("Tú: ").strip()
            
            if pregunta.lower() in ['salir', 'exit', 'quit']:
                print("¡Hasta luego!")
                break
            
            if not pregunta:
                continue
            
            # Añadir mensaje del usuario
            mensajes.append(HumanMessage(content=pregunta))
            
            # Obtener respuesta
            respuesta = llm.invoke(mensajes)
            
            # Añadir respuesta al historial
            mensajes.append(respuesta)
            
            print(f"\nAgente: {respuesta.content}\n")
            
        except KeyboardInterrupt:
            print("\n¡Hasta luego!")
            break
        except Exception as e:
            print(f"Error: {str(e)}\n")

if __name__ == "__main__":
    main()