"""Regla de revisión humana, decidida por código y no por el modelo.

Referencia: docs/02-contrato.md sección 4 y decisiones D2 y D3.
"""
import re
import unicodedata

from app.schemas import Category, EngineResult


def _normalizar(texto: str) -> str:
    """Minúsculas y sin marcas diacríticas (acentos)."""
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


TERMINOS_SEGURIDAD = (
    "vulnerabilidad",
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
    "se filtra",
    "se filtran",
    "se filtro",
    "filtrando",
    "filtrado",
    "filtrados",
    "filtraciones",
)


# Raíces: límite de palabra al inicio y cualquier terminación
# ("hacke" cubre hackeo, hackear, hackearon, hackeada, hackeos...).
RAICES_SEGURIDAD = ("hacke",)


def _patron_del_termino(termino: str) -> str:
    # Las palabras de un término pueden ir separadas por cualquier espacio, y
    # cada palabra acepta su plural con el sufijo opcional "s" o "es".
    return r"\s+".join(re.escape(palabra) + r"(?:es|s)?" for palabra in termino.split())


# Término exacto: palabra completa, no subcadena ("ese filtro" no contiene
# "se filtro"), con plural opcional en cada palabra.
# Raíz: límite de palabra al inicio y cualquier terminación.
_PATRON_TERMINOS = re.compile(
    r"\b(?:"
    + "|".join(
        [_patron_del_termino(_normalizar(t)) for t in TERMINOS_SEGURIDAD]
        + [re.escape(_normalizar(r)) + r"\w*" for r in RAICES_SEGURIDAD]
    )
    + r")\b"
)


def requires_human_review(message: str, result: EngineResult) -> bool:
    """True si el motor clasificó SECURITY o el mensaje contiene un término
    de seguridad, sin importar la categoría que haya devuelto el motor."""
    if result.category is Category.SECURITY:
        return True
    return _PATRON_TERMINOS.search(_normalizar(message)) is not None
