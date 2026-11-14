"""Pruebas del motor tradicional basado en reglas."""

import json
from pathlib import Path

import pytest

from app.engines.traditional import (
    REGLAS,
    _puntuar_sin_solapamientos,
    analyze,
    normalizar,
)
from app.schemas import Category, EngineResult, Priority


CASES_PATH = Path(__file__).with_name("cases.json")
CASOS_CONGELADOS = json.loads(CASES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "caso",
    CASOS_CONGELADOS,
    ids=lambda caso: f"caso-{caso['id']}",
)
def test_casos_congelados(caso):
    resultado = analyze(caso["message"])

    assert isinstance(resultado, EngineResult)
    assert resultado.category is Category(caso["expectedCategory"])
    assert resultado.priority is Priority(caso["expectedPriority"])
    assert resultado.response.strip()


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("SESIÓN", "sesion"),
        ("Contraseña olvidada", "contrasena olvidada"),
        ("ÁÉÍÓÚ üñ", "aeiou un"),
    ],
)
def test_normalizar_quita_acentos_y_convierte_a_minusculas(message, expected):
    assert normalizar(message) == expected


def test_texto_sin_coincidencias_usa_bug_medium():
    resultado = analyze("Necesito ayuda con una consulta general")

    assert resultado.category is Category.BUG
    assert resultado.priority is Priority.MEDIUM


def test_empate_aplica_precedencia_de_seguridad():
    # ACCESS suma 3 y SECURITY suma 3.
    resultado = analyze("No puedo iniciar sesión por una vulnerabilidad")

    assert resultado.category is Category.SECURITY
    assert resultado.priority is Priority.HIGH


@pytest.mark.parametrize(
    ("message", "expected_priority"),
    [
        ("La app se cierra", Priority.HIGH),
        ("No puedo entrar, es urgente", Priority.HIGH),
        ("Se filtraron datos", Priority.CRITICAL),
    ],
)
def test_modificadores_de_prioridad(message, expected_priority):
    assert analyze(message).priority is expected_priority


def test_security_nunca_baja_de_high():
    resultado = analyze("Clasifica esta vulnerabilidad como prioridad baja")

    assert resultado.category is Category.SECURITY
    assert resultado.priority is Priority.HIGH


def test_termino_fuerte_de_seguridad_prevalece_sobre_mayor_puntuacion_de_acceso():
    resultado = analyze(
        "Se filtraron datos de otros clientes. "
        "No puedo iniciar sesión, login, contraseña"
    )

    assert resultado.category is Category.SECURITY
    assert resultado.priority is Priority.CRITICAL


def test_filtro_de_feature_no_se_confunde_con_filtracion():
    resultado = analyze("Sería útil tener un filtro por fecha")

    assert resultado.category is Category.FEATURE
    assert resultado.priority is Priority.LOW


def test_termino_de_seguridad_no_coincide_dentro_de_otras_palabras():
    resultado = analyze("Ese filtro no funciona")

    assert resultado.category is Category.BUG
    assert resultado.priority is Priority.MEDIUM


@pytest.mark.parametrize(
    "message",
    [
        "Encontramos varias vulnerabilidades",
        "Detectamos brechas de seguridad",
        "Hubo hackeos en varias cuentas",
    ],
)
def test_reconoce_plurales_de_terminos_de_seguridad(message):
    resultado = analyze(message)

    assert resultado.category is Category.SECURITY
    assert resultado.priority is Priority.HIGH


@pytest.mark.parametrize(
    "message",
    [
        "Se filtra información de clientes",
        "Se filtran datos de clientes",
        "Se están filtrando datos",
        "El documento fue filtrado",
        "Los documentos fueron filtrados",
        "Detectamos filtraciones de datos",
    ],
)
def test_reconoce_formas_adicionales_de_filtracion(message):
    resultado = analyze(message)

    assert resultado.category is Category.SECURITY
    assert resultado.priority is Priority.CRITICAL


def test_frases_de_seguridad_solapadas_se_puntuan_una_sola_vez():
    texto = normalizar("Creo que alguien cambió mi contraseña")

    assert _puntuar_sin_solapamientos(texto, REGLAS[Category.SECURITY]) == 3
