"""Pruebas de la regla de revisión humana (app/review.py).

Referencia: docs/02-contrato.md sección 4 y decisiones D2 y D3.
"""
import pytest

from app.review import TERMINOS_SEGURIDAD, requires_human_review
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


TERMINOS_DE_FILTRACION = [
    "se filtra",
    "se filtran",
    "se filtro",
    "filtrando",
    "filtrado",
    "filtrados",
    "filtraciones",
]


@pytest.mark.parametrize("termino", TERMINOS_DE_FILTRACION)
def test_cada_termino_de_filtracion_activa_la_revision(termino):
    mensaje = f"Aviso importante: {termino} en el sistema"

    assert requires_human_review(mensaje, resultado(Category.BUG))


@pytest.mark.parametrize(
    "mensaje",
    ["Se filtra información de clientes", "Se están filtrando datos de la base"],
)
def test_filtracion_en_presente_con_categoria_bug_requiere_revision(mensaje):
    assert requires_human_review(mensaje, resultado(Category.BUG)) is True


@pytest.mark.parametrize(
    "mensaje", ["Ese filtro no funciona", "Sería útil un filtro por fecha"]
)
def test_filtro_de_una_interfaz_con_categoria_feature_no_requiere_revision(mensaje):
    assert requires_human_review(mensaje, resultado(Category.FEATURE)) is False


@pytest.mark.parametrize(
    "mensaje",
    [
        "Ese filtro no funciona",
        "Tengo un infiltrado en la lista de contactos",
        "Mi cuenta de vulnerabilidades_x no carga",
    ],
)
def test_los_terminos_se_buscan_como_palabra_completa_no_como_subcadena(mensaje):
    assert requires_human_review(mensaje, resultado(Category.BUG)) is False


def test_un_termino_de_varias_palabras_tolera_espacios_y_saltos_de_linea():
    assert requires_human_review(
        "Hubo acceso   no\nautorizado a mi cuenta", resultado(Category.BUG)
    )


def test_un_termino_pegado_a_signos_de_puntuacion_se_detecta():
    assert requires_human_review("¡Phishing!", resultado(Category.BUG))
    assert requires_human_review("(se filtra), creo", resultado(Category.BUG))


@pytest.mark.parametrize(
    "mensaje",
    [
        "Reportaron varias vulnerabilidades",
        "Hubo dos brechas este mes",
        "Detectamos hackeos",
    ],
)
def test_los_terminos_aceptan_su_plural(mensaje):
    assert requires_human_review(mensaje, resultado(Category.BUG)) is True


@pytest.mark.parametrize("sufijo", ["s", "es"])
@pytest.mark.parametrize("termino", TERMINOS_SEGURIDAD)
def test_cada_termino_acepta_el_sufijo_s_o_es(termino, sufijo):
    mensaje = f"Aviso: {termino}{sufijo} en el sistema"

    assert requires_human_review(mensaje, resultado(Category.BUG))


@pytest.mark.parametrize(
    "mensaje",
    [
        "Ese filtro no funciona",
        "Ese filtros no funciona",
        "Tengo vulnerabilidadesx en mi lista",
        "Hay brechass de sobra",
    ],
)
def test_el_plural_no_rompe_el_limite_de_palabra(mensaje):
    assert requires_human_review(mensaje, resultado(Category.BUG)) is False


@pytest.mark.parametrize(
    "mensaje",
    [
        "Me hackearon la cuenta",
        "Mi cuenta fue hackeada",
        "Detectamos accesos no autorizados",
    ],
)
def test_raiz_hacke_y_plural_en_cada_palabra_requieren_revision(mensaje):
    assert requires_human_review(mensaje, resultado(Category.BUG)) is True


@pytest.mark.parametrize(
    "mensaje",
    ["Sufrimos un hackeo", "Hay que hackear esto", "Hubo hackeos", "Hackers en la red"],
)
def test_la_raiz_hacke_acepta_cualquier_terminacion(mensaje):
    assert requires_human_review(mensaje, resultado(Category.BUG)) is True


def test_la_raiz_exige_limite_de_palabra_al_inicio():
    assert requires_human_review("El archivo chackeado", resultado(Category.BUG)) is False


@pytest.mark.parametrize(
    "mensaje",
    [
        "Hubo accesos no autorizados",
        "Un acceso no autorizado",
        "Accesos no autorizado",
        "Acceso no autorizados",
        "Vimos contraseñas expuestas",
    ],
)
def test_los_terminos_de_varias_palabras_aceptan_plural_en_cada_palabra(mensaje):
    assert requires_human_review(mensaje, resultado(Category.BUG)) is True


def test_devuelve_un_booleano():
    assert requires_human_review("hola", resultado(Category.BUG)) is False
    assert requires_human_review("phishing", resultado(Category.BUG)) is True
