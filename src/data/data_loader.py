from src.data.data_processor_pandas import DataProcessorPandas
import sys
import os

# Añadir el directorio padre al path para importar config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def main():
    print("=" * 35)
    print("     INICIANDO LA CARGA DE DATOS (VERSION PANDAS)")
    print("=" * 35)

    try:
        # [CAMBIO]: Usamos la nueva clase DataProcessorPandas
        procesador = DataProcessorPandas()                           # Crear instancia del procesador de datos CON PANDAS
        coleccion = procesador.load_data_to_chroma(batch_size=1000)  # Cargar datos
        
        if coleccion:
            print("\n > ¡Datos cargados correctamente exitosamente! (Usando Pandas)")
            print(f" > Total de documentos en la coleccion: {coleccion.count()}")

            print("\n > Estadisticas de la coleccion:")
            print(f"    - Modelo de embeddings cargado correctamente: {procesador.model.__class__.__name__}")
            print(f"    - Nombre de la coleccion: {coleccion.name}")

        else:
            print("\n > ERROR: No se pudieron cargar los datos en ChromaDB.")
            sys.exit(1)

    except Exception as e:            
        print(f"\n > ERROR FATAL: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
