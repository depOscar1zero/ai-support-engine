"""Pruebas del contrato compartido (app/schemas.py).

La referencia es docs/02-contrato.md, secciones 1 y 3.
"""
import pytest
from pydantic import ValidationError

from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    Category,
    EngineResult,
    Mode,
    Priority,
)


def campos_con_error(exc_info) -> set[str]:
    """Nombres de los campos que fallaron la validación."""
    return {error["loc"][0] for error in exc_info.value.errors()}


# --- AnalyzeRequest --------------------------------------------------------


@pytest.mark.parametrize("mode", ["traditional", "generative"])
def test_peticion_valida(mode):
    req = AnalyzeRequest(message="No puedo iniciar sesión", mode=mode)

    assert req.message == "No puedo iniciar sesión"
    assert req.mode is Mode(mode)


def test_mode_invalido_es_rechazado():
    with pytest.raises(ValidationError) as exc_info:
        AnalyzeRequest(message="No puedo iniciar sesión", mode="hibrido")

    assert campos_con_error(exc_info) == {"mode"}


def test_message_vacio_es_rechazado():
    with pytest.raises(ValidationError) as exc_info:
        AnalyzeRequest(message="", mode="traditional")

    assert campos_con_error(exc_info) == {"message"}


@pytest.mark.parametrize("message", ["   ", "\t", "\n", " \t\n "])
def test_message_solo_espacios_es_rechazado(message):
    with pytest.raises(ValidationError) as exc_info:
        AnalyzeRequest(message=message, mode="traditional")

    assert campos_con_error(exc_info) == {"message"}


def test_message_de_2001_caracteres_es_rechazado():
    with pytest.raises(ValidationError) as exc_info:
        AnalyzeRequest(message="a" * 2001, mode="traditional")

    assert campos_con_error(exc_info) == {"message"}


def test_message_de_2000_caracteres_es_aceptado():
    # Frontera: asegura que el límite es 2000 y no un valor menor.
    req = AnalyzeRequest(message="a" * 2000, mode="traditional")

    assert len(req.message) == 2000


# --- EngineResult / AnalyzeResponse ---------------------------------------


@pytest.mark.parametrize("category", list(Category))
@pytest.mark.parametrize("priority", list(Priority))
def test_engine_result_acepta_todos_los_valores_permitidos(category, priority):
    # Evita que las pruebas de rechazo pasen solo porque el modelo
    # rechaza todo.
    result = EngineResult(
        category=category.value, priority=priority.value, response="Gracias."
    )

    assert result.category is category
    assert result.priority is priority


@pytest.mark.parametrize("category", ["OTHER", "access", ""])
def test_category_fuera_de_los_valores_permitidos_es_rechazada(category):
    with pytest.raises(ValidationError) as exc_info:
        EngineResult(category=category, priority="LOW", response="Gracias.")

    assert campos_con_error(exc_info) == {"category"}


@pytest.mark.parametrize("priority", ["URGENT", "low", ""])
def test_priority_fuera_de_los_valores_permitidos_es_rechazada(priority):
    with pytest.raises(ValidationError) as exc_info:
        EngineResult(category="BUG", priority=priority, response="Gracias.")

    assert campos_con_error(exc_info) == {"priority"}


def test_analyze_response_agrega_revision_humana_y_mode():
    response = AnalyzeResponse(
        category="SECURITY",
        priority="CRITICAL",
        response="Escalamos su caso.",
        requiresHumanReview=True,
        mode="generative",
    )

    assert response.requiresHumanReview is True
    assert response.mode is Mode.generative
