"""Pruebas de POST /api/analyze con motores falsos (sin red ni Gemini).

Referencia: docs/02-contrato.md secciones 1 y 2; decisiones D2, D3 y D4.
"""
import logging

import pytest
from fastapi.testclient import TestClient

from app.engines import EngineError, generative, traditional
from app.main import MENSAJE_502, app, origenes_permitidos
from app.schemas import Category, EngineResult, Priority

CLAVE_FALSA = "AIzaSyFAKE-CLAVE-DE-PRUEBA-0000"
DETALLE_INTERNO = "detalle-interno-del-proveedor-xyz"
CAMPOS_RESPUESTA = {
    "category",
    "priority",
    "response",
    "requiresHumanReview",
    "mode",
}


def resultado(category=Category.FEATURE, response="Gracias.") -> EngineResult:
    return EngineResult(category=category, priority=Priority.LOW, response=response)


@pytest.fixture(autouse=True)
def motores_falsos(monkeypatch):
    """Ningún test llega a un motor real: ambos devuelven FEATURE por defecto."""
    monkeypatch.setattr(traditional, "analyze", lambda message: resultado())
    monkeypatch.setattr(generative, "analyze", lambda message: resultado())


@pytest.fixture
def client():
    return TestClient(app)


def post(client, message="No puedo iniciar sesión", mode="traditional"):
    return client.post("/api/analyze", json={"message": message, "mode": mode})


# --- 200 -------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["traditional", "generative"])
def test_peticion_valida_devuelve_200_con_los_cinco_campos(client, mode):
    response = post(client, mode=mode)

    assert response.status_code == 200
    assert set(response.json()) == CAMPOS_RESPUESTA


@pytest.mark.parametrize("mode", ["traditional", "generative"])
def test_mode_de_la_respuesta_coincide_con_el_pedido(client, mode):
    assert post(client, mode=mode).json()["mode"] == mode


def test_cada_mode_usa_su_propio_motor(client, monkeypatch):
    monkeypatch.setattr(
        traditional, "analyze", lambda message: resultado(response="del tradicional")
    )
    monkeypatch.setattr(
        generative, "analyze", lambda message: resultado(response="del generativo")
    )

    assert post(client, mode="traditional").json()["response"] == "del tradicional"
    assert post(client, mode="generative").json()["response"] == "del generativo"


def test_el_motor_recibe_el_mensaje_ya_normalizado_por_el_contrato(
    client, monkeypatch
):
    recibido = []

    def espia(message):
        recibido.append(message)
        return resultado()

    monkeypatch.setattr(traditional, "analyze", espia)

    post(client, message="  hola  ")

    assert recibido == ["hola"]


# --- 422 -------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"message": "hola", "mode": "hibrido"},
        {"message": "hola"},
        {"mode": "traditional"},
        {"message": "", "mode": "traditional"},
        {"message": "   ", "mode": "traditional"},
        {"message": "a" * 2001, "mode": "traditional"},
    ],
    ids=[
        "mode-invalido",
        "mode-faltante",
        "message-faltante",
        "message-vacio",
        "message-solo-espacios",
        "message-de-2001",
    ],
)
def test_peticion_invalida_devuelve_422(client, payload):
    assert client.post("/api/analyze", json=payload).status_code == 422


def test_peticion_invalida_no_llega_al_motor(client, monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        traditional, "analyze", lambda message: llamadas.append(message)
    )

    client.post("/api/analyze", json={"message": "", "mode": "traditional"})

    assert llamadas == []


# --- 502 (D4) --------------------------------------------------------------


@pytest.mark.parametrize("mode", ["traditional", "generative"])
def test_engine_error_devuelve_502_sin_el_mensaje_interno(
    client, monkeypatch, mode
):
    def falla(message):
        raise EngineError(DETALLE_INTERNO)

    monkeypatch.setattr(traditional, "analyze", falla)
    monkeypatch.setattr(generative, "analyze", falla)

    response = post(client, mode=mode)

    assert response.status_code == 502
    assert DETALLE_INTERNO not in response.text
    assert isinstance(response.json()["detail"], str)


@pytest.mark.parametrize("mode", ["traditional", "generative"])
def test_not_implemented_error_devuelve_502_sin_el_mensaje_interno(
    client, monkeypatch, mode
):
    def pendiente(message):
        raise NotImplementedError(DETALLE_INTERNO)

    monkeypatch.setattr(traditional, "analyze", pendiente)
    monkeypatch.setattr(generative, "analyze", pendiente)

    response = post(client, mode=mode)

    assert response.status_code == 502
    assert DETALLE_INTERNO not in response.text


def test_engine_error_encadenado_no_filtra_la_clave_ni_en_cuerpo_ni_en_logs(
    client, monkeypatch, caplog, capsys
):
    def falla_con_causa(message):
        try:
            raise RuntimeError(f"401 key={CLAVE_FALSA}")
        except RuntimeError as causa:
            raise EngineError("El proveedor no respondió.") from causa

    monkeypatch.setattr(generative, "analyze", falla_con_causa)

    with caplog.at_level(logging.DEBUG):
        response = post(client, mode="generative")

    salida = capsys.readouterr()
    assert response.status_code == 502
    assert CLAVE_FALSA not in response.text
    assert CLAVE_FALSA not in caplog.text
    assert CLAVE_FALSA not in salida.out + salida.err
    # Ningún registro lleva traceback ni excepción adjunta.
    assert all(r.exc_info is None and not r.exc_text for r in caplog.records)
    assert all(CLAVE_FALSA not in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("mode", ["traditional", "generative"])
def test_excepcion_inesperada_devuelve_502_y_no_filtra_la_clave(
    client, monkeypatch, caplog, capsys, mode
):
    def falla(message):
        raise RuntimeError(f"401 key={CLAVE_FALSA}")

    monkeypatch.setattr(traditional, "analyze", falla)
    monkeypatch.setattr(generative, "analyze", falla)

    with caplog.at_level(logging.DEBUG):
        response = post(client, mode=mode)

    salida = capsys.readouterr()
    assert response.status_code == 502
    assert response.json() == {"detail": MENSAJE_502}
    assert CLAVE_FALSA not in response.text
    assert CLAVE_FALSA not in caplog.text
    assert CLAVE_FALSA not in salida.out + salida.err
    assert all(r.exc_info is None and not r.exc_text for r in caplog.records)


def test_el_log_del_502_solo_trae_el_motor_y_la_clase_de_la_excepcion(
    client, monkeypatch, caplog
):
    def falla_con_causa(message):
        try:
            raise ValueError(f"mensaje-secreto {CLAVE_FALSA}")
        except ValueError as causa:
            raise KeyError("otro-secreto") from causa

    monkeypatch.setattr(generative, "analyze", falla_con_causa)

    with caplog.at_level(logging.DEBUG):
        post(client, mode="generative")

    mensajes = [r.getMessage() for r in caplog.records if r.name == "app.main"]
    assert len(mensajes) == 1
    assert "generative" in mensajes[0]
    assert "KeyError" in mensajes[0]
    for prohibido in ("otro-secreto", "mensaje-secreto", "ValueError", CLAVE_FALSA):
        assert prohibido not in caplog.text


def test_openapi_documenta_la_respuesta_502(client):
    operacion = client.get("/openapi.json").json()["paths"]["/api/analyze"]["post"]

    respuesta = operacion["responses"]["502"]
    assert respuesta["description"] == "El motor no pudo procesar la solicitud"
    esquema = respuesta["content"]["application/json"]["schema"]
    if "$ref" in esquema:
        nombre = esquema["$ref"].rsplit("/", 1)[-1]
        esquema = client.get("/openapi.json").json()["components"]["schemas"][nombre]
    assert esquema["properties"] == {
        "detail": {"type": "string", "title": "Detail"}
    }
    assert esquema["required"] == ["detail"]


# --- requiresHumanReview (D2 y D3) -----------------------------------------


def test_categoria_security_marca_revision_humana(client, monkeypatch):
    monkeypatch.setattr(
        traditional, "analyze", lambda message: resultado(Category.SECURITY)
    )

    assert post(client, message="Texto cualquiera").json()["requiresHumanReview"]


def test_feature_con_vulnerabilidad_marca_revision_humana(client):
    body = post(client, message="Sería útil corregir esta vulnerabilidad").json()

    assert body["category"] == "FEATURE"
    assert body["requiresHumanReview"] is True


def test_feature_sin_terminos_de_seguridad_no_marca_revision(client):
    body = post(client, message="Sería útil tener modo oscuro").json()

    assert body["category"] == "FEATURE"
    assert body["requiresHumanReview"] is False


# --- CORS ------------------------------------------------------------------


def preflight(client, origin):
    return client.options(
        "/api/analyze",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )


@pytest.mark.parametrize(
    "origin", ["http://localhost:3000", "http://127.0.0.1:5173"]
)
def test_cors_permite_origenes_locales_por_defecto(client, origin):
    response = preflight(client, origin)

    assert response.headers.get("access-control-allow-origin") == origin


def test_cors_rechaza_origenes_no_locales(client):
    response = preflight(client, "https://evil.example")

    assert "access-control-allow-origin" not in response.headers


def test_origenes_se_leen_de_la_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:9000, http://127.0.0.1:9001 ")

    assert origenes_permitidos() == [
        "http://localhost:9000",
        "http://127.0.0.1:9001",
    ]


def test_origenes_ignoran_los_no_locales_aunque_esten_en_la_variable(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS", "https://evil.example,*,http://localhost:9000"
    )

    assert origenes_permitidos() == ["http://localhost:9000"]


def test_origenes_tienen_valor_por_defecto_si_no_hay_variable(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    assert "http://localhost:3000" in origenes_permitidos()
