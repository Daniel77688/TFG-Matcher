"""
Cargador de datos — Procesa CSVs y los almacena en ChromaDB.

Uso:
    python -m src.data.data_loader
"""
import logging
import sys

from src.data.data_processor_pandas import DataProcessorPandas

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 50)
    logger.info("INICIANDO CARGA DE DATOS (Pandas + ChromaDB)")
    logger.info("=" * 50)

    try:
        procesador = DataProcessorPandas()
        coleccion = procesador.load_data_to_chroma(batch_size=1000)

        if coleccion:
            logger.info("✅ Datos cargados correctamente")
            logger.info("Total documentos en colección: %d", coleccion.count())
            logger.info("Modelo de embeddings: %s", procesador.model.__class__.__name__)
            logger.info("Nombre de colección: %s", coleccion.name)
        else:
            logger.error("No se pudieron cargar los datos en ChromaDB")
            sys.exit(1)

    except Exception as e:
        logger.error("ERROR FATAL: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
