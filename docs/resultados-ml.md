# Resultados del motor de Machine Learning

Evaluación realizada el 18 de noviembre de 2026 con Python 3.13.0,
pandas 3.1.1 y scikit-learn 1.9.1.

## Dataset

- Archivo: `data/tickets.csv`.
- Registros: 200.
- Distribución: 50 `ACCESS`, 50 `BUG`, 50 `FEATURE` y 50 `SECURITY`.
- Valores nulos o vacíos: 0.
- Mensajes duplicados después de normalizar: 0.
- Coincidencias con los 22 casos reservados de evaluación: 0.
- Datos personales, secretos o fórmulas CSV detectados: 0.

## División de entrenamiento

Se utilizó una división estratificada reproducible con `random_state=42`:

- Entrenamiento: 160 registros.
- Prueba: 40 registros, 10 por categoría.

| Categoría | Precision | Recall | F1 |
|---|---:|---:|---:|
| ACCESS | 0.91 | 1.00 | 0.95 |
| BUG | 0.64 | 0.70 | 0.67 |
| FEATURE | 1.00 | 0.80 | 0.89 |
| SECURITY | 0.70 | 0.70 | 0.70 |
| **Promedio macro** | **0.81** | **0.80** | **0.80** |

La exactitud total del conjunto de prueba fue 80 %.

## Casos reservados

Los casos reservados no participaron en el entrenamiento ni en la selección
del vectorizador.

| Conjunto | Casos | Acierto estricto | Categoría | Formato | SECURITY con revisión |
|---|---:|---:|---:|---:|---:|
| Referencia | 12 | 8/12 (66.7 %) | 8/12 (66.7 %) | 12/12 (100 %) | 4/5 (80 %) |
| No vistos | 10 | 3/10 (30 %) | 6/10 (60 %) | 10/10 (100 %) | 1/2 (50 %) |

## Interpretación

El motor es funcional como línea base local: siempre cumplió el contrato y no
depende de red durante la inferencia. Su principal límite es la generalización
a mensajes ambiguos, adversariales y prioridades que no se deducen solo de la
categoría. No debe presentarse como un clasificador de producción.

El ejemplo `Alguien entró a mi cuenta sin autorización` fue clasificado como
`ACCESS/MEDIUM`. La capa determinista de seguridad activa revisión humana para
la expresión `sin autorización`, de modo que el caso no pasa sin supervisión.

## Verificación técnica

- Suite: 351 pruebas aprobadas y 3 omitidas.
- Endpoint real con `mode=ml`: HTTP 200.
- Artefacto local: `models/ticket_classifier.joblib` (ignorado por Git y
  reproducible con `python -m scripts.train_ml`).
