"""Pruebas de la demo web servida en la raíz (frontend/).

Referencia: docs/01-arquitectura.md y decisión D9 (login solo visual).
"""
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.engines import generative, ml, traditional
from app.main import app
from app.schemas import Category, EngineResult, Priority

RAIZ = Path(__file__).resolve().parent.parent
FRONTEND = RAIZ / "frontend"
CASOS = {
    c["id"]: c["message"]
    for c in json.loads((RAIZ / "tests" / "cases.json").read_text(encoding="utf-8"))
}

# Ids que app.js usa; cambiarlos rompe la lógica (ver frontend/README.md).
IDS_QUE_USA_APP_JS = [
    "login-section",
    "login-form",
    "login-user",
    "login-password",
    "app-section",
    "analyze-form",
    "message-input",
    "char-counter",
    "mode-select",
    "submit-button",
    "loading-indicator",
    "error-message",
    "result-section",
    "result-category",
    "result-priority",
    "result-response",
    "result-mode",
    "review-warning",
    "history-list",
    "history-empty",
]


@pytest.fixture(autouse=True)
def motores_falsos(monkeypatch):
    res = EngineResult(
        category=Category.FEATURE, priority=Priority.LOW, response="Gracias."
    )
    monkeypatch.setattr(traditional, "analyze", lambda message: res)
    monkeypatch.setattr(generative, "analyze", lambda message: res)
    monkeypatch.setattr(ml, "analyze", lambda message: res)


@pytest.fixture
def client():
    return TestClient(app)


class _Recolector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.ejemplos = []
        self.hojas = []
        self.scripts = []
        self.atributos_style = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if "data-example-message" in a:
            self.ejemplos.append(a["data-example-message"])
        if tag == "link" and a.get("rel") == "stylesheet":
            self.hojas.append(a.get("href"))
        if tag == "script":
            self.scripts.append(a.get("src"))
        if "style" in a:
            self.atributos_style += 1


@pytest.fixture(scope="module")
def html():
    texto = (FRONTEND / "index.html").read_text(encoding="utf-8")
    r = _Recolector()
    r.feed(texto)
    return texto, r


def test_get_raiz_responde_200_con_la_pagina(client):
    r = client.get("/")

    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<html" in r.text.lower()


@pytest.mark.parametrize(
    ("ruta", "tipo"),
    [("/styles.css", "text/css"), ("/app.js", "javascript")],
)
def test_se_sirven_los_estaticos(client, ruta, tipo):
    r = client.get(ruta)

    assert r.status_code == 200
    assert tipo in r.headers["content-type"]


def test_post_api_analyze_sigue_igual(client):
    r = client.post(
        "/api/analyze", json={"message": "No puedo iniciar sesión", "mode": "traditional"}
    )

    assert r.status_code == 200
    assert r.json() == {
        "category": "FEATURE",
        "priority": "LOW",
        "response": "Gracias.",
        "requiresHumanReview": False,
        "mode": "traditional",
    }


def test_post_invalido_sigue_devolviendo_422(client):
    r = client.post("/api/analyze", json={"message": "   ", "mode": "traditional"})

    assert r.status_code == 422


def test_get_a_api_analyze_no_lo_captura_el_frontend(client):
    # La ruta de la API tiene prioridad sobre los estáticos: GET no es POST.
    assert client.get("/api/analyze").status_code == 405


def test_una_ruta_inexistente_devuelve_404(client):
    assert client.get("/no-existe.txt").status_code == 404


def test_el_html_enlaza_styles_y_app_con_rutas_relativas(html):
    _, r = html

    assert r.hojas == ["styles.css"]
    assert r.scripts == ["app.js"]


@pytest.mark.parametrize("identificador", IDS_QUE_USA_APP_JS)
def test_el_html_tiene_los_ids_que_usa_app_js(html, identificador):
    _, r = html

    assert r.ids.count(identificador) == 1


@pytest.mark.parametrize("identificador", IDS_QUE_USA_APP_JS)
def test_app_js_referencia_cada_id_que_declara_el_contrato(identificador):
    js = (FRONTEND / "app.js").read_text(encoding="utf-8")

    assert identificador in js


def test_los_ejemplos_son_los_casos_1_5_7_y_11_de_cases_json(html):
    _, r = html

    assert r.ejemplos == [CASOS[1], CASOS[5], CASOS[7], CASOS[11]]


def test_el_html_declara_que_el_login_es_demostrativo(html):
    texto, _ = html
    plano = re.sub(r"<[^>]+>", " ", texto).lower()

    assert "demostrativ" in plano
    assert "no protege" in plano


def test_el_textarea_usa_el_maximo_del_contrato(html):
    texto, _ = html

    assert 'maxlength="2000"' in texto


def test_el_frontend_ofrece_el_motor_ml(html):
    texto, _ = html

    assert '<option value="ml">Machine Learning</option>' in texto
    assert 'ml: "Machine Learning"' in (FRONTEND / "app.js").read_text(encoding="utf-8")


def test_el_html_no_trae_estilos_en_linea(html):
    texto, r = html

    assert r.atributos_style == 0
    assert "<style" not in texto.lower()


def test_app_js_no_usa_innerhtml_ni_equivalentes():
    js = (FRONTEND / "app.js").read_text(encoding="utf-8")

    for prohibido in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
        assert prohibido not in js


def test_app_js_no_genera_estilos():
    js = (FRONTEND / "app.js").read_text(encoding="utf-8")

    for prohibido in (".style.", ".style[", "cssText", 'setAttribute("style"', "setAttribute('style'"):
        assert prohibido not in js


def test_el_frontend_no_contiene_claves_ni_secretos():
    for nombre in ("index.html", "app.js", "styles.css", "README.md"):
        texto = (FRONTEND / nombre).read_text(encoding="utf-8")

        assert "GEMINI_API_KEY" not in texto
        assert not re.search(r"AIza[0-9A-Za-z_-]{20,}", texto)


def test_styles_define_las_variables_css_al_inicio():
    css = (FRONTEND / "styles.css").read_text(encoding="utf-8")
    primer_bloque = css[: css.index("}") + 1]

    assert ":root" in primer_bloque
    for grupo in ("--color-", "--font-", "--space-"):
        assert grupo in primer_bloque


def test_el_readme_del_frontend_explica_que_se_puede_cambiar():
    texto = (FRONTEND / "README.md").read_text(encoding="utf-8")

    assert "styles.css" in texto
    assert "app.js" in texto
    assert "id" in texto
