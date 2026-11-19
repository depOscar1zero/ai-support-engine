"""Motor de Machine Learning entrenado fuera del proceso de la API.

El artefacto se genera con ``python -m scripts.train_ml``. La carga es
diferida para que la API pueda arrancar aunque el modelo todavía no exista.
"""
import os
from functools import lru_cache
from pathlib import Path

import joblib

from app.engines import EngineError
from app.engines import traditional
from app.schemas import Category, EngineResult


RAIZ = Path(__file__).resolve().parent.parent.parent
MODELO_POR_DEFECTO = RAIZ / "models" / "ticket_classifier.joblib"


def ruta_modelo() -> Path:
    """Ruta del artefacto, configurable mediante ``ML_MODEL_PATH``."""
    configurada = os.environ.get("ML_MODEL_PATH")
    if not configurada:
        return MODELO_POR_DEFECTO
    ruta = Path(configurada).expanduser()
    return ruta if ruta.is_absolute() else RAIZ / ruta


@lru_cache(maxsize=1)
def _cargar_modelo(ruta: str):
    """Carga y valida mínimamente un artefacto generado por el proyecto."""
    archivo = Path(ruta)
    if not archivo.is_file():
        raise EngineError("El modelo de Machine Learning no está entrenado.")

    try:
        artefacto = joblib.load(archivo)
        modelo = artefacto["model"]
        categorias = set(artefacto["categories"])
    except EngineError:
        raise
    except Exception:
        raise EngineError("El modelo de Machine Learning no es válido.") from None

    permitidas = {categoria.value for categoria in Category}
    if categorias != permitidas or not callable(getattr(modelo, "predict", None)):
        raise EngineError("El modelo de Machine Learning no es compatible.")
    return modelo


def limpiar_cache() -> None:
    """Permite recargar un modelo recién entrenado y aislar pruebas."""
    _cargar_modelo.cache_clear()


def analyze(message: str) -> EngineResult:
    """Predice la categoría y completa el contrato con reglas deterministas."""
    try:
        modelo = _cargar_modelo(str(ruta_modelo().resolve()))
        prediccion = modelo.predict([message])
        if len(prediccion) != 1:
            raise EngineError("El modelo devolvió una predicción inválida.")
        category = Category(str(prediccion[0]))
    except EngineError:
        raise
    except Exception:
        raise EngineError("El modelo no pudo clasificar la solicitud.") from None

    texto = traditional.normalizar(message)
    return EngineResult(
        category=category,
        priority=traditional.priorizar(texto, category),
        response=traditional.RESPUESTAS[category],
    )
