"""Pruebas de la regla de revisión humana (app/review.py).

Referencia: docs/02-contrato.md sección 4 y decisiones D2 y D3.
"""
import pytest

from app.review import requires_human_review
from app.schemas import Category, EngineResult, Priority

TERMINOS_INICIALES = [
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
]


def resultado(category: Category) -> EngineResult:
    return EngineResult(
        category=category, priority=Priority.LOW, response="Gracias."
    )


def test_categoria_security_requiere_revision_sin_terminos():
    assert requires_human_review(
        "Mensaje sin ningún término especial", resultado(Category.SECURITY)
    )


def test_feature_con_vulnerabilidad_requiere_revision():
    assert requires_human_review(
        "Sería útil corregir esta vulnerabilidad", resultado(Category.FEATURE)
    )


def test_feature_sin_terminos_no_requiere_revision():
    assert not requires_human_review(
        "Sería útil tener modo oscuro", resultado(Category.FEATURE)
    )


@pytest.mark.parametrize(
    "category", [Category.ACCESS, Category.BUG, Category.FEATURE]
)
def test_categorias_no_security_sin_terminos_no_requieren_revision(category):
    assert not requires_human_review("No puedo iniciar sesión", resultado(category))


@pytest.mark.parametrize("termino", TERMINOS_INICIALES)
@pytest.mark.parametrize(
    "category", [Category.ACCESS, Category.BUG, Category.FEATURE]
)
def test_cada_termino_inicial_activa_la_revision(termino, category):
    mensaje = f"Quiero avisar de algo: {termino} en la plataforma"

    assert requires_human_review(mensaje, resultado(category))


@pytest.mark.parametrize(
    "mensaje",
    [
        "VULNERABILIDAD",
        "Encontré una Vulnerabilidad",
        "FILTRACIÓN de datos",
        "filtracion de datos",
        "Inyeccion SQL",
        "INYECCIÓN SQL",
        "ACCESO NO AUTORIZADO a mi cuenta",
        "contrasenas expuestas",
    ],
)
def test_comparacion_ignora_mayusculas_y_acentos(mensaje):
    assert requires_human_review(mensaje, resultado(Category.FEATURE))


def test_devuelve_un_booleano():
    assert requires_human_review("hola", resultado(Category.BUG)) is False
    assert requires_human_review("phishing", resultado(Category.BUG)) is True
