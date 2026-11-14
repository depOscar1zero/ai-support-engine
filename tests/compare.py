"""Comparativa de los dos motores contra los casos de evaluación.

Uso:
    python -m tests.compare [--mode traditional|generative] [--delay 3]

Llama a POST /api/analyze (con TestClient) por cada caso y cada motor, y
escribe docs/resultados.md. Referencia: docs/02-contrato.md sección 5 y
decisión D11.

El reporte nunca incluye la API key ni mensajes de error internos: de una
respuesta fallida solo se guarda el código HTTP.
"""
import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from app.schemas import AnalyzeResponse

RAIZ = Path(__file__).resolve().parent.parent
CASOS_REFERENCIA = RAIZ / "tests" / "cases.json"
CASOS_NO_VISTOS = RAIZ / "tests" / "cases_no_vistos.json"
SALIDA = RAIZ / "docs" / "resultados.md"

MODOS = ("traditional", "generative")
MODELO_POR_DEFECTO = "gemini-3.8-flash"
CAMPOS_CASO = ("message", "expectedCategory", "expectedPriority", "type")
LARGO_MENSAJE_EN_LISTA = 80


# --- carga de casos --------------------------------------------------------


def cargar_casos(ruta):
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if not isinstance(datos, list):
        raise ValueError(f"{Path(ruta).name}: se esperaba una lista de casos")
    for posicion, caso in enumerate(datos, start=1):
        faltan = [campo for campo in CAMPOS_CASO if campo not in caso]
        if faltan:
            raise ValueError(
                f"{Path(ruta).name}: al caso {posicion} le faltan {', '.join(faltan)}"
            )
    return datos


def cargar_conjuntos(casos, no_vistos):
    """Devuelve (conjuntos existentes, nombres de archivos que no existen)."""
    conjuntos = [
        {
            "nombre": "referencia",
            "archivo": Path(casos).name,
            "casos": cargar_casos(casos),
        }
    ]
    omitidos = []
    if Path(no_vistos).exists():
        conjuntos.append(
            {
                "nombre": "no vistos",
                "archivo": Path(no_vistos).name,
                "casos": cargar_casos(no_vistos),
            }
        )
    else:
        omitidos.append(Path(no_vistos).name)
    return conjuntos, omitidos


# --- ejecución -------------------------------------------------------------


def ejecutar_caso(client, caso, modo):
    """Llama al endpoint para un caso y un modo, y registra el resultado.

    Un 502, un cuerpo que no cumple AnalyzeResponse, un mode distinto al
    pedido o un fallo del cliente cuentan como formato incumplido e
    incorrecto. Nunca se guarda el cuerpo de un error.
    """
    registro = {
        "id": caso.get("id"),
        "tipo": caso["type"],
        "modo": modo,
        "mensaje": caso["message"],
        "esperada_categoria": caso["expectedCategory"],
        "esperada_prioridad": caso["expectedPriority"],
        "http": None,
        "category": None,
        "priority": None,
        "revision": None,
        "formato": False,
        "correcto": False,
        "categoria_correcta": False,
    }
    try:
        respuesta = client.post(
            "/api/analyze", json={"message": caso["message"], "mode": modo}
        )
    except Exception:
        return registro

    registro["http"] = respuesta.status_code
    if respuesta.status_code != 200:
        return registro
    try:
        valida = AnalyzeResponse.model_validate(respuesta.json())
    except (ValueError, ValidationError):
        return registro
    if valida.mode.value != modo:
        return registro

    categoria_ok = valida.category.value == caso["expectedCategory"]
    prioridad_ok = valida.priority.value == caso["expectedPriority"]
    registro.update(
        category=valida.category.value,
        priority=valida.priority.value,
        revision=valida.requiresHumanReview,
        formato=True,
        categoria_correcta=categoria_ok,
        correcto=categoria_ok and prioridad_ok,
    )
    return registro


def ejecutar(client, conjuntos, modos, delay, sleep=time.sleep, progreso=None):
    registros = []
    llamadas_generativas = 0
    for modo in modos:
        for conjunto in conjuntos:
            for caso in conjunto["casos"]:
                if modo == "generative":
                    if llamadas_generativas and delay > 0:
                        sleep(delay)
                    llamadas_generativas += 1
                registro = ejecutar_caso(client, caso, modo)
                registro["conjunto"] = conjunto["nombre"]
                registros.append(registro)
                if progreso:
                    progreso(registro)
    return registros


# --- resumen y reporte -----------------------------------------------------


def formatear_porcentaje(aciertos, total):
    if total == 0:
        return "n/a"
    return f"{aciertos}/{total} ({100 * aciertos / total:.1f}%)"


def resumir(registros):
    """Conteos por (modo, conjunto)."""
    resumen = {}
    for r in registros:
        s = resumen.setdefault(
            (r["modo"], r["conjunto"]),
            {
                "casos": 0,
                "estricto": 0,
                "categoria": 0,
                "formato": 0,
                "seguridad_esperada": 0,
                "seguridad_marcada": 0,
            },
        )
        s["casos"] += 1
        s["estricto"] += int(r["correcto"])
        s["categoria"] += int(r["categoria_correcta"])
        s["formato"] += int(r["formato"])
        if r["esperada_categoria"] == "SECURITY":
            s["seguridad_esperada"] += 1
            s["seguridad_marcada"] += int(r["revision"] is True)
    return resumen


def _celda(texto):
    return str(texto).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _si_no(valor):
    return "Sí" if valor else "No"


def _obtenido(r):
    if r["formato"]:
        return f"{r['category']}/{r['priority']}"
    if r["http"] is None:
        return "sin respuesta válida (sin respuesta)"
    return f"sin respuesta válida (HTTP {r['http']})"


def _recortar(mensaje):
    mensaje = " ".join(str(mensaje).split())
    if len(mensaje) > LARGO_MENSAJE_EN_LISTA:
        mensaje = mensaje[: LARGO_MENSAJE_EN_LISTA - 3] + "..."
    return mensaje


def generar_reporte(registros, resumen, conjuntos, omitidos, modos, modelo, ahora):
    lineas = [
        "# Resultados de la comparativa",
        "",
        "> Generado por script (`python -m tests.compare`). No editar a mano: "
        "se sobrescribe en cada ejecución.",
        "",
        f"- Fecha y hora: {ahora.strftime('%Y-%m-%d %H:%M:%S %z')}",
        f"- Modelo generativo: {modelo}",
        f"- Motores ejecutados: {', '.join(modos)}",
    ]
    for conjunto in conjuntos:
        lineas.append(
            f"- Conjunto {conjunto['nombre']}: `{conjunto['archivo']}`, "
            f"{len(conjunto['casos'])} casos."
        )
    for archivo in omitidos:
        lineas.append(
            f"- Conjunto no vistos: `{archivo}` no existe; se continuó solo con "
            "los demás conjuntos."
        )

    lineas += [
        "",
        "## Resumen",
        "",
        "| Motor | Conjunto | Casos | Acierto estricto | Acierto de categoría "
        "| Cumplimiento de formato | SECURITY esperada con revisión humana |",
        "|---|---|---|---|---|---|---|",
    ]
    for modo in modos:
        for conjunto in conjuntos:
            s = resumen[(modo, conjunto["nombre"])]
            lineas.append(
                f"| {modo} | {conjunto['nombre']} | {s['casos']} "
                f"| {formatear_porcentaje(s['estricto'], s['casos'])} "
                f"| {formatear_porcentaje(s['categoria'], s['casos'])} "
                f"| {formatear_porcentaje(s['formato'], s['casos'])} "
                f"| {formatear_porcentaje(s['seguridad_marcada'], s['seguridad_esperada'])} |"
            )
    lineas += [
        "",
        "Criterios: un caso es **correcto** (acierto estricto) solo si coinciden "
        "categoría y prioridad; el acierto de categoría cuenta solo la categoría. "
        "Un 502 o una respuesta que no cumple el formato cuenta como formato "
        "incumplido e incorrecto.",
        "",
        "## Resultados por motor y conjunto",
    ]

    for modo in modos:
        for conjunto in conjuntos:
            filas = [
                r
                for r in registros
                if r["modo"] == modo and r["conjunto"] == conjunto["nombre"]
            ]
            lineas += [
                "",
                f"### {modo} - {conjunto['nombre']} ({len(filas)} casos)",
                "",
                "| # | Tipo | HTTP | Esperado | Obtenido | Revisión humana "
                "| Formato | Correcto | Categoría correcta |",
                "|---|---|---|---|---|---|---|---|---|",
            ]
            for r in filas:
                revision = "-" if r["revision"] is None else _si_no(r["revision"])
                http = "-" if r["http"] is None else r["http"]
                obtenido = f"{r['category']}/{r['priority']}" if r["formato"] else "-"
                lineas.append(
                    f"| {_celda(r['id'])} | {_celda(r['tipo'])} | {http} "
                    f"| {r['esperada_categoria']}/{r['esperada_prioridad']} "
                    f"| {obtenido} | {revision} | {_si_no(r['formato'])} "
                    f"| {_si_no(r['correcto'])} | {_si_no(r['categoria_correcta'])} |"
                )

    fallados = [r for r in registros if not r["correcto"]]
    lineas += ["", "## Casos fallados", ""]
    if not fallados:
        lineas.append("Ninguno.")
    for r in fallados:
        lineas.append(
            f"- {r['modo']} / {r['conjunto']} / caso {r['id']} ({r['tipo']}): "
            f"esperado {r['esperada_categoria']}/{r['esperada_prioridad']}, "
            f"obtenido {_obtenido(r)} - \"{_recortar(r['mensaje'])}\""
        )
    return "\n".join(lineas) + "\n"


def ejecutar_comparativa(
    modos,
    delay,
    salida,
    casos,
    no_vistos,
    client,
    sleep=time.sleep,
    ahora=None,
    progreso=None,
):
    conjuntos, omitidos = cargar_conjuntos(casos, no_vistos)
    registros = ejecutar(client, conjuntos, modos, delay, sleep, progreso)
    resumen = resumir(registros)

    if "generative" in modos:
        modelo = os.environ.get("GEMINI_MODEL") or (
            f"{MODELO_POR_DEFECTO} (por defecto; GEMINI_MODEL no está definido)"
        )
    else:
        modelo = "no usado en esta ejecución"
    texto = generar_reporte(
        registros,
        resumen,
        conjuntos,
        omitidos,
        modos,
        modelo,
        ahora or datetime.now().astimezone(),
    )

    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(texto, encoding="utf-8", newline="\n")
    return {"registros": registros, "resumen": resumen, "salida": salida}


# --- línea de comandos -----------------------------------------------------


def _crear_cliente():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


def _imprimir_progreso(r):
    estado = "OK" if r["correcto"] else "X"
    http = "-" if r["http"] is None else r["http"]
    print(f"{r['modo']} | {r['conjunto']} | caso {r['id']}: HTTP {http} {estado}")


def main(argv=None, client=None):
    parser = argparse.ArgumentParser(
        prog="python -m tests.compare",
        description="Compara ambos motores contra los casos de evaluación y "
        "escribe docs/resultados.md.",
    )
    parser.add_argument(
        "--mode", choices=MODOS, help="correr un solo motor (por defecto, ambos)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="segundos de pausa entre llamadas generativas (por defecto 3)",
    )
    parser.add_argument("--output", type=Path, default=SALIDA, help="reporte de salida")
    parser.add_argument("--cases", type=Path, default=CASOS_REFERENCIA)
    parser.add_argument(
        "--no-vistos", dest="no_vistos", type=Path, default=CASOS_NO_VISTOS
    )
    args = parser.parse_args(argv)
    if args.delay < 0:
        parser.error("--delay no puede ser negativo")

    if client is None:
        client = _crear_cliente()
    modos = (args.mode,) if args.mode else MODOS
    corrida = ejecutar_comparativa(
        modos=modos,
        delay=args.delay,
        salida=args.output,
        casos=args.cases,
        no_vistos=args.no_vistos,
        client=client,
        progreso=_imprimir_progreso,
    )

    print()
    for (modo, conjunto), s in corrida["resumen"].items():
        print(
            f"{modo} / {conjunto}: estricto {formatear_porcentaje(s['estricto'], s['casos'])}, "
            f"categoria {formatear_porcentaje(s['categoria'], s['casos'])}, "
            f"formato {formatear_porcentaje(s['formato'], s['casos'])}"
        )
    print(f"Reporte escrito en {corrida['salida']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
