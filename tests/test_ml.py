"""Pruebas del motor local de Machine Learning."""
import joblib
import pytest

from app.engines import EngineError, ml
from app.schemas import Category, EngineResult, Priority


class ModeloFalso:
    def __init__(self, category):
        self.category = category
        self.calls = []

    def predict(self, messages):
        self.calls.append(messages)
        return [self.category]


@pytest.fixture(autouse=True)
def cache_limpia():
    ml.limpiar_cache()
    yield
    ml.limpiar_cache()


def guardar_modelo(ruta, category="FEATURE"):
    joblib.dump(
        {
            "model": ModeloFalso(category),
            "categories": [categoria.value for categoria in Category],
        },
        ruta,
    )


def test_falta_de_modelo_lanza_engine_error(tmp_path, monkeypatch):
    monkeypatch.setenv("ML_MODEL_PATH", str(tmp_path / "no-existe.joblib"))

    with pytest.raises(EngineError):
        ml.analyze("Quiero modo oscuro")


def test_artefacto_incompatible_lanza_engine_error(tmp_path, monkeypatch):
    ruta = tmp_path / "incompatible.joblib"
    joblib.dump({"model": ModeloFalso("BUG"), "categories": ["BUG"]}, ruta)
    monkeypatch.setenv("ML_MODEL_PATH", str(ruta))

    with pytest.raises(EngineError):
        ml.analyze("La aplicación falla")


def test_prediccion_cumple_engine_result(tmp_path, monkeypatch):
    ruta = tmp_path / "modelo.joblib"
    guardar_modelo(ruta, "FEATURE")
    monkeypatch.setenv("ML_MODEL_PATH", str(ruta))

    resultado = ml.analyze("Sería útil agregar reportes")

    assert isinstance(resultado, EngineResult)
    assert resultado.category is Category.FEATURE
    assert resultado.priority is Priority.LOW
    assert resultado.response.strip()


def test_seguridad_conserva_prioridad_determinista(tmp_path, monkeypatch):
    ruta = tmp_path / "modelo.joblib"
    guardar_modelo(ruta, "SECURITY")
    monkeypatch.setenv("ML_MODEL_PATH", str(ruta))

    resultado = ml.analyze("Se filtraron los datos de otros clientes")

    assert resultado.category is Category.SECURITY
    assert resultado.priority is Priority.CRITICAL


def test_modelo_se_carga_una_sola_vez(tmp_path, monkeypatch):
    ruta = tmp_path / "modelo.joblib"
    guardar_modelo(ruta)
    monkeypatch.setenv("ML_MODEL_PATH", str(ruta))
    cargas = []
    original = joblib.load

    def carga_espiada(archivo):
        cargas.append(archivo)
        return original(archivo)

    monkeypatch.setattr(ml.joblib, "load", carga_espiada)

    ml.analyze("mensaje uno")
    ml.analyze("mensaje dos")

    assert len(cargas) == 1
