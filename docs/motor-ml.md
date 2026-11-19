# Motor de Machine Learning

El tercer motor clasifica tickets con un pipeline local de TF-IDF y regresión
logística. Expone el mismo contrato que los demás:

```python
def analyze(message: str) -> EngineResult
```

## Dataset

El archivo está versionado en `data/tickets.csv` después de comprobar que no
contiene datos personales ni secretos. Debe tener las columnas necesarias
`message` y `category`; puede tener columnas adicionales, que no participan
en el entrenamiento.

Las categorías admitidas son `ACCESS`, `BUG`, `FEATURE` y `SECURITY`. El
validador rechaza valores nulos o vacíos, categorías desconocidas, categorías
ausentes, mensajes duplicados y coincidencias exactas con los casos reservados
de `tests/cases.json` y `tests/cases_no_vistos.json`.

## Entrenamiento

Desde la raíz del repositorio:

```bash
python -m scripts.train_ml --validate-only
python -m scripts.train_ml
```

`--validate-only` permite revisar el archivo entregado sin entrenar ni escribir
un artefacto.

Opciones disponibles:

```bash
python -m scripts.train_ml --data ruta/tickets.csv \
  --output ruta/modelo.joblib --test-size 0.2
```

La división es estratificada y usa `random_state=42`. El comando imprime la
distribución, el reporte de clasificación y la matriz de confusión. El
artefacto incluye el pipeline, las categorías, metadatos básicos y las
métricas de esa corrida.

## Inferencia

Por defecto, `app/engines/ml.py` busca
`models/ticket_classifier.joblib`. `ML_MODEL_PATH` permite cambiar esa ruta.
El archivo se carga una sola vez por proceso. Si no existe, está corrupto o no
contiene las cuatro categorías del contrato, el motor lanza `EngineError` y la
API devuelve el mismo 502 genérico que utiliza para los demás motores.

La predicción decide únicamente la categoría. La prioridad y la respuesta se
calculan con las reglas deterministas del motor tradicional; la revisión
humana continúa en `app/review.py`, fuera del modelo.

Los archivos `.joblib` usan serialización de Python y solo deben cargarse si
fueron generados por este proyecto y provienen de una fuente confiable.
