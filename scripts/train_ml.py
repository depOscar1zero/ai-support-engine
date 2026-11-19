"""Valida tickets.csv, entrena el clasificador y guarda su artefacto.

Uso desde la raíz del repositorio:
    python -m scripts.train_ml
"""
import argparse
import json
import math
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


RAIZ = Path(__file__).resolve().parent.parent
DATASET_POR_DEFECTO = RAIZ / "data" / "tickets.csv"
MODELO_POR_DEFECTO = RAIZ / "models" / "ticket_classifier.joblib"
CATEGORIAS = ("ACCESS", "BUG", "FEATURE", "SECURITY")
COLUMNAS = ("message", "category")
SEMILLA = 42
CASOS_DE_EVALUACION = (
    Path(__file__).resolve().parent.parent / "tests" / "cases.json",
    Path(__file__).resolve().parent.parent / "tests" / "cases_no_vistos.json",
)


class DatasetError(ValueError):
    """El CSV no cumple el contrato necesario para entrenar."""


def _clave_mensaje(message: str) -> str:
    """Normaliza lo suficiente para detectar duplicados y fuga de datos."""
    texto = unicodedata.normalize("NFD", " ".join(message.split()).casefold())
    return "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )


def cargar_y_validar(ruta: Path) -> pd.DataFrame:
    """Carga el CSV sin corregir silenciosamente errores de etiquetado."""
    ruta = Path(ruta)
    if not ruta.is_file():
        raise DatasetError(f"No existe el dataset: {ruta}")

    try:
        datos = pd.read_csv(ruta)
    except Exception as exc:
        raise DatasetError(f"No se pudo leer {ruta.name}: {type(exc).__name__}") from None

    faltantes = [columna for columna in COLUMNAS if columna not in datos.columns]
    if faltantes:
        raise DatasetError(f"Faltan columnas obligatorias: {', '.join(faltantes)}")

    datos = datos.loc[:, list(COLUMNAS)].copy()
    if datos.empty:
        raise DatasetError("El dataset está vacío.")
    if datos[list(COLUMNAS)].isnull().any().any():
        raise DatasetError("El dataset contiene mensajes o categorías nulas.")
    if not datos["message"].map(lambda valor: isinstance(valor, str)).all():
        raise DatasetError("Todos los mensajes deben ser texto.")
    if not datos["category"].map(lambda valor: isinstance(valor, str)).all():
        raise DatasetError("Todas las categorías deben ser texto.")

    datos["message"] = datos["message"].str.strip()
    datos["category"] = datos["category"].str.strip()
    if datos["message"].eq("").any() or datos["category"].eq("").any():
        raise DatasetError("El dataset contiene mensajes o categorías vacías.")
    if datos["message"].str.len().gt(2000).any():
        raise DatasetError("El dataset contiene mensajes de más de 2000 caracteres.")

    desconocidas = sorted(set(datos["category"]) - set(CATEGORIAS))
    if desconocidas:
        raise DatasetError("Categorías no permitidas: " + ", ".join(desconocidas))

    ausentes = sorted(set(CATEGORIAS) - set(datos["category"]))
    if ausentes:
        raise DatasetError("Faltan ejemplos de: " + ", ".join(ausentes))

    claves = datos["message"].map(_clave_mensaje)
    duplicados = claves[claves.duplicated(keep=False)]
    if not duplicados.empty:
        raise DatasetError(
            f"Hay {duplicados.nunique()} mensajes duplicados; deben revisarse antes de entrenar."
        )

    conteos = datos["category"].value_counts()
    insuficientes = conteos[conteos < 2]
    if not insuficientes.empty:
        detalle = ", ".join(
            f"{categoria}={cantidad}"
            for categoria, cantidad in insuficientes.items()
        )
        raise DatasetError("Cada categoría necesita al menos 2 ejemplos: " + detalle)
    return datos


def crear_pipeline() -> Pipeline:
    return Pipeline(
        [
            (
                "vectorizer",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    strip_accents="unicode",
                    lowercase=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=SEMILLA,
                ),
            ),
        ]
    )


def validar_sin_fuga(datos: pd.DataFrame, archivos=CASOS_DE_EVALUACION) -> None:
    """Impide entrenar con mensajes reservados para evaluar los motores."""
    mensajes_entrenamiento = {_clave_mensaje(mensaje) for mensaje in datos["message"]}
    coincidencias = []
    for archivo in map(Path, archivos):
        if not archivo.is_file():
            continue
        try:
            casos = json.loads(archivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise DatasetError(
                f"No se pudo validar el archivo de evaluación: {archivo.name}"
            ) from None
        for caso in casos:
            mensaje = str(caso.get("message", "")).strip()
            if _clave_mensaje(mensaje) in mensajes_entrenamiento:
                coincidencias.append(f"{archivo.name}: caso {caso.get('id', '?')}")
    if coincidencias:
        raise DatasetError(
            "El dataset contiene mensajes reservados para evaluación: "
            + ", ".join(coincidencias)
        )


def entrenar(
    dataset: Path = DATASET_POR_DEFECTO,
    salida: Path = MODELO_POR_DEFECTO,
    test_size: float = 0.2,
) -> dict:
    if not 0 < test_size < 1:
        raise DatasetError("test_size debe estar entre 0 y 1.")

    datos = cargar_y_validar(dataset)
    total_prueba = math.ceil(len(datos) * test_size)
    total_entrenamiento = len(datos) - total_prueba
    if min(total_prueba, total_entrenamiento) < len(CATEGORIAS):
        raise DatasetError(
            "La división no deja al menos un ejemplo de cada categoría en entrenamiento y prueba."
        )

    validar_sin_fuga(datos)

    X_train, X_test, y_train, y_test = train_test_split(
        datos["message"],
        datos["category"],
        test_size=test_size,
        stratify=datos["category"],
        random_state=SEMILLA,
    )
    modelo = crear_pipeline()
    modelo.fit(X_train, y_train)
    predicciones = modelo.predict(X_test)

    reporte_texto = classification_report(
        y_test,
        predicciones,
        labels=list(CATEGORIAS),
        zero_division=0,
    )
    reporte = classification_report(
        y_test,
        predicciones,
        labels=list(CATEGORIAS),
        output_dict=True,
        zero_division=0,
    )
    matriz = confusion_matrix(y_test, predicciones, labels=list(CATEGORIAS)).tolist()
    artefacto = {
        "model": modelo,
        "categories": list(CATEGORIAS),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_rows": len(datos),
        "random_state": SEMILLA,
        "test_size": test_size,
        "metrics": reporte,
        "confusion_matrix": matriz,
    }

    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    temporal = salida.with_suffix(salida.suffix + ".tmp")
    try:
        joblib.dump(artefacto, temporal)
        temporal.replace(salida)
    finally:
        temporal.unlink(missing_ok=True)

    return {
        "dataset_rows": len(datos),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "category_counts": datos["category"].value_counts().sort_index().to_dict(),
        "report": reporte_texto,
        "confusion_matrix": matriz,
        "output": salida,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.train_ml",
        description="Entrena el clasificador de tickets de soporte.",
    )
    parser.add_argument("--data", type=Path, default=DATASET_POR_DEFECTO)
    parser.add_argument("--output", type=Path, default=MODELO_POR_DEFECTO)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="valida el CSV sin entrenar ni escribir un modelo",
    )
    args = parser.parse_args(argv)

    try:
        if args.validate_only:
            datos = cargar_y_validar(args.data)
            validar_sin_fuga(datos)
            print(f"Dataset válido: {len(datos)} registros")
            distribucion = datos["category"].value_counts().sort_index().to_dict()
            print("Distribución:", distribucion)
            return 0
        resultado = entrenar(args.data, args.output, args.test_size)
    except DatasetError as exc:
        parser.error(str(exc))

    print(f"Dataset: {resultado['dataset_rows']} registros")
    print(f"Entrenamiento: {resultado['train_rows']}")
    print(f"Prueba: {resultado['test_rows']}")
    print("Distribución:", resultado["category_counts"])
    print("\nReporte de clasificación:\n")
    print(resultado["report"])
    print("Matriz de confusión (ACCESS, BUG, FEATURE, SECURITY):")
    for fila in resultado["confusion_matrix"]:
        print(fila)
    print(f"\nModelo guardado en: {resultado['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
