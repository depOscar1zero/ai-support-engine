"""Pruebas del proceso reproducible de entrenamiento."""
import json

import pandas as pd
import pytest

from scripts.train_ml import (
    DatasetError,
    cargar_y_validar,
    entrenar,
    main,
    validar_sin_fuga,
)


CATEGORIAS = ("ACCESS", "BUG", "FEATURE", "SECURITY")


def datos_validos(cantidad_por_categoria=5):
    return pd.DataFrame(
        [
            {
                "message": f"mensaje único {categoria} {numero}",
                "category": categoria,
            }
            for categoria in CATEGORIAS
            for numero in range(cantidad_por_categoria)
        ]
    )


def guardar_csv(tmp_path, datos=None):
    ruta = tmp_path / "tickets.csv"
    (datos if datos is not None else datos_validos()).to_csv(ruta, index=False)
    return ruta


def test_rechaza_csv_sin_columnas_obligatorias(tmp_path):
    ruta = tmp_path / "tickets.csv"
    pd.DataFrame({"texto": ["hola"]}).to_csv(ruta, index=False)

    with pytest.raises(DatasetError, match="Faltan columnas"):
        cargar_y_validar(ruta)


def test_rechaza_categoria_desconocida(tmp_path):
    datos = datos_validos()
    datos.loc[0, "category"] = "OTHER"

    with pytest.raises(DatasetError, match="no permitidas"):
        cargar_y_validar(guardar_csv(tmp_path, datos))


def test_rechaza_mensajes_duplicados(tmp_path):
    datos = datos_validos()
    datos.loc[1, "message"] = datos.loc[0, "message"]

    with pytest.raises(DatasetError, match="duplicados"):
        cargar_y_validar(guardar_csv(tmp_path, datos))


def test_detecta_fuga_con_casos_de_evaluacion(tmp_path):
    datos = datos_validos()
    mensaje = datos.iloc[0]["message"]
    casos = tmp_path / "casos.json"
    casos.write_text(json.dumps([{"id": 7, "message": mensaje}]), encoding="utf-8")

    with pytest.raises(DatasetError, match="reservados para evaluación"):
        validar_sin_fuga(datos, archivos=(casos,))


def test_entrena_y_guarda_artefacto(tmp_path):
    ruta = guardar_csv(tmp_path)
    salida = tmp_path / "models" / "modelo.joblib"

    resultado = entrenar(ruta, salida, test_size=0.2)

    assert salida.is_file()
    assert resultado["dataset_rows"] == 20
    assert resultado["train_rows"] == 16
    assert resultado["test_rows"] == 4
    assert set(resultado["category_counts"]) == set(CATEGORIAS)
    assert resultado["demo_message"] == "Encontré datos de otros clientes"
    assert resultado["demo_category"] in CATEGORIAS
    assert 0 <= resultado["demo_confidence"] <= 1


def test_validate_only_no_crea_modelo(tmp_path, capsys):
    ruta = guardar_csv(tmp_path)
    salida = tmp_path / "modelo.joblib"

    codigo = main(
        ["--data", str(ruta), "--output", str(salida), "--validate-only"]
    )

    assert codigo == 0
    assert not salida.exists()
    assert "Dataset válido: 20 registros" in capsys.readouterr().out
