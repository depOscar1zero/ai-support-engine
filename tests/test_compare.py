"""Pruebas de tests/compare.py con motores falsos: sin red ni pausas.

Referencia: docs/02-contrato.md sección 5 y decisión D11.
"""
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.engines import generative, traditional
from app.main import app
from app.schemas import Category, EngineResult, Priority
from tests import compare

CLAVE_FALSA = "AIzaSyFAKE-CLAVE-DE-PRUEBA-0000"
DETALLE_INTERNO = "detalle-interno-secreto-987"
AHORA = datetime(2026, 11, 14, 18, 30, tzinfo=timezone.utc)


def caso(id_, message, categoria, prioridad, tipo="normal"):
    return {
        "id": id_,
        "message": message,
        "type": tipo,
        "expectedCategory": categoria,
        "expectedPriority": prioridad,
    }


def resultado(categoria, prioridad):
    return EngineResult(
        category=Category(categoria),
        priority=Priority(prioridad),
        response="Gracias.",
    )


# Qué devuelve el motor falso para cada mensaje (categoría, prioridad).
RESPUESTAS = {
    "mensaje a": ("ACCESS", "MEDIUM"),
    "mensaje b": ("BUG", "LOW"),
    "mensaje c": ("BUG", "LOW"),
    "mensaje d": ("SECURITY", "HIGH"),
    "mensaje e": ("FEATURE", "LOW"),
}

# a: correcto | b: solo categoría | c: incorrecto | d: correcto | e: incorrecto
CASOS = [
    caso(1, "mensaje a", "ACCESS", "MEDIUM"),
    caso(2, "mensaje b", "BUG", "HIGH"),
    caso(3, "mensaje c", "FEATURE", "LOW", "ambiguous"),
    caso(4, "mensaje d", "SECURITY", "HIGH"),
    caso(5, "mensaje e", "SECURITY", "CRITICAL", "adversarial"),
]


def motor_falso(message):
    return resultado(*RESPUESTAS[message])


@pytest.fixture(autouse=True)
def motores_falsos(monkeypatch):
    monkeypatch.setattr(traditional, "analyze", motor_falso)
    monkeypatch.setattr(generative, "analyze", motor_falso)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def guardar(ruta, casos):
    ruta.write_text(json.dumps(casos, ensure_ascii=False), encoding="utf-8")


def correr(
    client,
    tmp_path,
    casos=CASOS,
    no_vistos=None,
    modos=compare.MODOS,
    delay=0,
    pausas=None,
):
    ruta_casos = tmp_path / "cases.json"
    ruta_no_vistos = tmp_path / "cases_no_vistos.json"
    guardar(ruta_casos, casos)
    if no_vistos is not None:
        guardar(ruta_no_vistos, no_vistos)
    return compare.ejecutar_comparativa(
        modos=modos,
        delay=delay,
        salida=tmp_path / "resultados.md",
        casos=ruta_casos,
        no_vistos=ruta_no_vistos,
        client=client,
        sleep=(pausas.append if pausas is not None else (lambda segundos: None)),
        ahora=AHORA,
    )


def texto(corrida):
    return corrida["salida"].read_text(encoding="utf-8")


# --- porcentajes -----------------------------------------------------------


def test_calcula_los_cuatro_porcentajes_por_motor_y_conjunto(client, tmp_path):
    corrida = correr(client, tmp_path)

    for modo in compare.MODOS:
        resumen = corrida["resumen"][(modo, "referencia")]
        assert resumen["casos"] == 5
        assert resumen["estricto"] == 2  # a y d
        assert resumen["categoria"] == 3  # a, b y d
        assert resumen["formato"] == 5
        assert resumen["seguridad_esperada"] == 2  # d y e
        assert resumen["seguridad_marcada"] == 1  # solo d

    informe = texto(corrida)
    assert "2/5 (40.0%)" in informe
    assert "3/5 (60.0%)" in informe
    assert "5/5 (100.0%)" in informe
    assert "1/2 (50.0%)" in informe


def test_porcentaje_sin_casos_no_divide_entre_cero():
    assert compare.formatear_porcentaje(0, 0) == "n/a"
    assert compare.formatear_porcentaje(1, 3) == "1/3 (33.3%)"


def test_cada_fila_registra_los_campos_pedidos(client, tmp_path):
    corrida = correr(client, tmp_path, modos=("traditional",))

    fila = next(r for r in corrida["registros"] if r["id"] == 2)
    assert fila["http"] == 200
    assert fila["category"] == "BUG"
    assert fila["priority"] == "LOW"
    assert fila["revision"] is False
    assert fila["formato"] is True
    assert fila["correcto"] is False
    assert fila["categoria_correcta"] is True


def test_lista_los_casos_fallados_con_esperado_y_obtenido(client, tmp_path):
    informe = texto(correr(client, tmp_path))

    assert "esperado BUG/HIGH, obtenido BUG/LOW" in informe
    assert "esperado FEATURE/LOW, obtenido BUG/LOW" in informe
    assert "esperado SECURITY/CRITICAL, obtenido FEATURE/LOW" in informe


# --- 502 y formato ---------------------------------------------------------


def test_un_502_cuenta_como_formato_incumplido_e_incorrecto_y_continua(
    client, tmp_path, monkeypatch
):
    def generativo(message):
        if message == "mensaje b":
            raise RuntimeError(f"{DETALLE_INTERNO} {CLAVE_FALSA}")
        return motor_falso(message)

    monkeypatch.setattr(generative, "analyze", generativo)

    corrida = correr(client, tmp_path)

    generativos = [r for r in corrida["registros"] if r["modo"] == "generative"]
    assert len(generativos) == 5  # la ejecución no se detuvo
    caido = next(r for r in generativos if r["id"] == 2)
    assert caido["http"] == 502
    assert caido["formato"] is False
    assert caido["correcto"] is False
    assert caido["categoria_correcta"] is False
    assert corrida["resumen"][("generative", "referencia")]["formato"] == 4
    assert corrida["resumen"][("traditional", "referencia")]["formato"] == 5


def test_el_reporte_no_guarda_claves_ni_errores_internos(
    client, tmp_path, monkeypatch
):
    def generativo(message):
        raise RuntimeError(f"{DETALLE_INTERNO} {CLAVE_FALSA}")

    monkeypatch.setattr(generative, "analyze", generativo)
    monkeypatch.setenv("GEMINI_API_KEY", CLAVE_FALSA)

    informe = texto(correr(client, tmp_path))

    assert CLAVE_FALSA not in informe
    assert DETALLE_INTERNO not in informe
    assert "AIza" not in informe


class RespuestaFalsa:
    def __init__(self, status, cuerpo=None, json_valido=True):
        self.status_code = status
        self._cuerpo = cuerpo
        self._json_valido = json_valido

    def json(self):
        if not self._json_valido:
            raise ValueError("no es JSON")
        return self._cuerpo


class ClienteFalso:
    def __init__(self, respuesta=None, error=None):
        self._respuesta = respuesta
        self._error = error

    def post(self, url, json):
        if self._error:
            raise self._error
        return self._respuesta


CUERPO_VALIDO = {
    "category": "BUG",
    "priority": "HIGH",
    "response": "Gracias.",
    "requiresHumanReview": False,
    "mode": "traditional",
}


@pytest.mark.parametrize(
    "cliente",
    [
        ClienteFalso(RespuestaFalsa(200, {"category": "OTRA"})),
        ClienteFalso(RespuestaFalsa(200, json_valido=False)),
        ClienteFalso(RespuestaFalsa(500)),
        ClienteFalso(RespuestaFalsa(502, {"detail": "x"})),
        ClienteFalso(RespuestaFalsa(200, {**CUERPO_VALIDO, "mode": "generative"})),
        ClienteFalso(error=RuntimeError(DETALLE_INTERNO)),
    ],
    ids=[
        "campos-invalidos",
        "no-es-json",
        "http-500",
        "http-502",
        "mode-distinto-al-pedido",
        "el-cliente-lanza",
    ],
)
def test_respuesta_que_no_cumple_el_formato_es_incorrecta(cliente):
    fila = compare.ejecutar_caso(cliente, CASOS[1], "traditional")

    assert fila["formato"] is False
    assert fila["correcto"] is False
    assert fila["categoria_correcta"] is False


def test_respuesta_valida_de_un_cliente_falso_es_correcta():
    cliente = ClienteFalso(RespuestaFalsa(200, CUERPO_VALIDO))

    fila = compare.ejecutar_caso(cliente, CASOS[1], "traditional")

    assert fila["formato"] is True
    assert fila["correcto"] is True


# --- casos no vistos y conteos --------------------------------------------


def test_sin_archivo_de_no_vistos_continua_con_la_referencia_y_lo_indica(
    client, tmp_path
):
    corrida = correr(client, tmp_path, no_vistos=None)

    informe = texto(corrida)
    assert "cases_no_vistos.json" in informe
    assert "no existe" in informe
    assert ("traditional", "no vistos") not in corrida["resumen"]
    assert "no vistos (" not in informe
    assert ("traditional", "referencia") in corrida["resumen"]


def test_el_conteo_coincide_con_los_archivos(client, tmp_path):
    no_vistos = [
        caso(101, "mensaje a", "ACCESS", "MEDIUM"),
        caso(102, "mensaje b", "BUG", "HIGH"),
        caso(103, "mensaje d", "SECURITY", "HIGH"),
    ]

    corrida = correr(client, tmp_path, no_vistos=no_vistos)

    for modo in compare.MODOS:
        assert corrida["resumen"][(modo, "referencia")]["casos"] == len(CASOS)
        assert corrida["resumen"][(modo, "no vistos")]["casos"] == len(no_vistos)
    assert len(corrida["registros"]) == (len(CASOS) + len(no_vistos)) * 2
    informe = texto(corrida)
    assert informe.count("referencia (5 casos)") == 2
    assert informe.count("no vistos (3 casos)") == 2


def test_el_conteo_coincide_con_el_cases_json_real(client, tmp_path, monkeypatch):
    reales = json.loads(compare.CASOS_REFERENCIA.read_text(encoding="utf-8"))
    monkeypatch.setattr(traditional, "analyze", lambda m: resultado("BUG", "LOW"))

    corrida = compare.ejecutar_comparativa(
        modos=("traditional",),
        delay=0,
        salida=tmp_path / "resultados.md",
        casos=compare.CASOS_REFERENCIA,
        no_vistos=tmp_path / "no_existe.json",
        client=client,
        sleep=lambda segundos: None,
        ahora=AHORA,
    )

    assert len(corrida["registros"]) == len(reales)
    assert f"referencia ({len(reales)} casos)" in texto(corrida)


# --- pausa, modos y reporte ------------------------------------------------


def test_pausa_solo_entre_llamadas_generativas(client, tmp_path):
    pausas = []

    correr(client, tmp_path, delay=2.5, pausas=pausas)

    assert pausas == [2.5] * (len(CASOS) - 1)


def test_modo_tradicional_no_llama_al_generativo_ni_pausa(
    client, tmp_path, monkeypatch
):
    llamadas = []
    monkeypatch.setattr(
        generative, "analyze", lambda m: llamadas.append(m) or motor_falso(m)
    )
    pausas = []

    corrida = correr(
        client, tmp_path, modos=("traditional",), delay=3, pausas=pausas
    )

    assert llamadas == []
    assert pausas == []
    assert {r["modo"] for r in corrida["registros"]} == {"traditional"}


def test_el_reporte_trae_fecha_modelo_y_aviso_de_script(
    client, tmp_path, monkeypatch
):
    monkeypatch.setenv("GEMINI_MODEL", "modelo-de-prueba")

    informe = texto(correr(client, tmp_path))

    assert "2026-11-14 18:30" in informe
    assert "modelo-de-prueba" in informe
    assert "Generado por script" in informe


def test_main_escribe_el_reporte_donde_se_le_indica(client, tmp_path):
    salida = tmp_path / "carpeta" / "resultados.md"

    codigo = compare.main(
        [
            "--mode", "traditional",
            "--delay", "0",
            "--output", str(salida),
            "--no-vistos", str(tmp_path / "no_existe.json"),
        ],
        client=client,
    )

    assert codigo == 0
    assert salida.exists()
    assert "Motores ejecutados: traditional" in salida.read_text(encoding="utf-8")


def test_main_rechaza_un_delay_negativo(client, tmp_path):
    with pytest.raises(SystemExit):
        compare.main(["--delay", "-1", "--output", str(tmp_path / "x.md")], client=client)
