"""Regla de revisión humana, decidida por código y no por el modelo.

Referencia: docs/02-contrato.md sección 4 y decisiones D2 y D3.
"""
import unicodedata

from app.schemas import Category, EngineResult


def _normalizar(texto: str) -> str:
    """Minúsculas y sin marcas diacríticas (acentos)."""
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


TERMINOS_SEGURIDAD = (
    "vulnerabilidad",
    "hackeo",
    "hackear",
    "filtración",
    "filtraron",
    "phishing",
    "brecha",
    "inyección",
    "malware",
    "ransomware",
    "acceso no autorizado",
    "datos de otros",
    "contraseñas expuestas",
    "sospechoso",
)

_TERMINOS_NORMALIZADOS = tuple(_normalizar(t) for t in TERMINOS_SEGURIDAD)


def requires_human_review(message: str, result: EngineResult) -> bool:
    """True si el motor clasificó SECURITY o el mensaje contiene un término
    de seguridad, sin importar la categoría que haya devuelto el motor."""
    if result.category is Category.SECURITY:
        return True
    texto = _normalizar(message)
    return any(termino in texto for termino in _TERMINOS_NORMALIZADOS)
