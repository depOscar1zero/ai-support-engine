"""Pruebas del motor generativo.

Grupo 1: sin internet, con un cliente falso (no gastan cuota).
Grupo 2: con internet, solo si RUN_INTERNET_TESTS=1 (pocas llamadas).
"""
import json
import os
from pathlib import Path

import pytest

from app.engines import EngineError, generative
from app.schemas import Category, EngineResult, Priority

CASES = json.loads((Path(__file__).parent / "cases.json").read_text(encoding="utf-8"))


# ---------- Cliente falso ----------
class _FakeResponse:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def __init__(self, text=None, exc=None):
        self._text = text
        self._exc = exc

    def generate_content(self, **kwargs):
        if self._exc:
            raise self._exc
        return _FakeResponse(self._text)


class _FakeClient:
    def __init__(self, text=None, exc=None):
        self.models = _FakeModels(text, exc)


@pytest.fixture
def usar_cliente(monkeypatch):
    def _usar(text=None, exc=None):
        monkeypatch.setattr(generative, "_get_client", lambda: _FakeClient(text, exc))
    return _usar


# ---------- Grupo 1: sin internet ----------
def test_respuesta_valida_devuelve_engine_result(usar_cliente):
    usar_cliente(text='{"category":"ACCESS","priority":"MEDIUM","response":"Hola"}')
    r = generative.analyze("No puedo iniciar sesión")
    assert isinstance(r, EngineResult)
    assert r.category == Category.ACCESS
    assert r.priority == Priority.MEDIUM


def test_excepcion_del_proveedor_lanza_engine_error(usar_cliente):
    usar_cliente(exc=RuntimeError("503 UNAVAILABLE"))
    with pytest.raises(EngineError):
        generative.analyze("hola")


def test_el_error_no_filtra_detalles_internos(usar_cliente):
    usar_cliente(exc=RuntimeError("clave-secreta-123"))
    with pytest.raises(EngineError) as e:
        generative.analyze("hola")
    assert "clave-secreta-123" not in str(e.value)


def test_texto_que_no_es_json_lanza_engine_error(usar_cliente):
    usar_cliente(text="esto no es json")
    with pytest.raises(EngineError):
        generative.analyze("hola")


def test_respuesta_vacia_lanza_engine_error(usar_cliente):
    usar_cliente(text=None)
    with pytest.raises(EngineError):
        generative.analyze("hola")


def test_categoria_fuera_del_contrato_lanza_engine_error(usar_cliente):
    usar_cliente(text='{"category":"OTRA","priority":"LOW","response":"x"}')
    with pytest.raises(EngineError):
        generative.analyze("hola")


def test_sin_api_key_lanza_engine_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(generative, "_client", None)
    with pytest.raises(EngineError):
        generative.analyze("hola")


# ---------- Grupo 2: con internet (apagado por defecto) ----------
internet = pytest.mark.skipif(
    os.environ.get("RUN_INTERNET_TESTS") != "1",
    reason="Gasta cuota de Gemini; activar con RUN_INTERNET_TESTS=1",
)


def _caso(id_):
    return next(c for c in CASES if c["id"] == id_)


@internet
def test_internet_no_puedo_iniciar_sesion():
    r = generative.analyze(_caso(1)["message"])
    assert r.category == Category.ACCESS


@internet
@pytest.mark.parametrize("id_", [11, 12])
def test_internet_casos_adversariales(id_):
    r = generative.analyze(_caso(id_)["message"])
    assert r.category == Category.SECURITY
    assert r.priority in (Priority.HIGH, Priority.CRITICAL)