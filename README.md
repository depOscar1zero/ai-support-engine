# 🤖 AI Support Engine
 
Prototipo de clasificación inteligente de solicitudes de soporte. Compara tres enfoques sobre el mismo contrato de API:
 
- **Motor tradicional:** reglas y condiciones en Python, sin modelo generativo.
- **Motor generativo:** Gemini 3.1 Flash-Lite mediante API.
- **Motor ML:** TF-IDF y regresión logística entrenados con tickets etiquetados.
Cada solicitud recibe una categoría (`ACCESS`, `BUG`, `FEATURE`, `SECURITY`), una prioridad (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), una respuesta para el usuario y una marca de revisión humana.
 
> **Estado:** en desarrollo. Entrega: lunes 16 de noviembre de 2026.
 
## 👥 Equipo
 
| Integrante | Responsabilidad |
|---|---|
| Alejandro Contreras Martínez | Motor tradicional |
| Lilia Tun Hernández | Motor generativo y diseño de la demo |
| Oscar Espinoza Landeta | API, validación, revisión humana y pruebas comparativas |
 
## 📁 Estructura
 
```
app/
  schemas.py          contrato compartido
  main.py             FastAPI + POST /api/analyze
  review.py           reglas de revisión humana
  engines/
    traditional.py    motor de reglas
    generative.py     motor con Gemini
    ml.py             inferencia del modelo entrenado
scripts/
  train_ml.py         validación, entrenamiento y evaluación
data/
  tickets.csv         dataset etiquetado para entrenamiento
models/               artefactos entrenados (ignorados por Git)
frontend/             demo visual
tests/
  cases.json          casos con clasificación de referencia
  compare.py          comparativa de los motores
docs/                 arquitectura, contrato y decisiones
```
 
## ⚙️ Instalación
 
Requiere Python 3.11 o superior.
 
```bash
git clone <url-del-repo>
cd ai-support-engine
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
 
## 🔑 Configuración
 
Copia `.env.example` como `.env` y coloca tu API key de Gemini:
 
```
GEMINI_API_KEY=tu_key
GEMINI_MODEL=gemini-3.1-flash-lite
```
 
El archivo `.env` está ignorado por git. **Nunca subas la key al repositorio.**

## Entrenamiento del motor ML

El dataset está en `data/tickets.csv`. Debe tener las columnas
`message` y `category`; las categorías permitidas son `ACCESS`, `BUG`,
`FEATURE` y `SECURITY`. El artefacto entrenado está ignorado por Git porque es
un binario generado y puede reproducirse desde el CSV.

```bash
python -m scripts.train_ml --validate-only
python -m scripts.train_ml
```

El primer comando comprueba el archivo sin entrenar. El segundo vuelve a
validarlo, impide usar los casos reservados de evaluación, imprime las métricas
y genera `models/ticket_classifier.joblib`. Es posible usar otra ruta de
inferencia mediante `ML_MODEL_PATH`.
 
## ▶️ Ejecución
 
```bash
uvicorn app.main:app --reload
```
 
La documentación interactiva queda en `http://127.0.0.1:8000/docs`.
 
## 📡 Uso
 
```bash
curl -X POST http://127.0.0.1:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"message": "No puedo iniciar sesión", "mode": "traditional"}'
```
 
```json
{
  "category": "ACCESS",
  "priority": "MEDIUM",
  "response": "Lamentamos el inconveniente. Verifique sus credenciales y utilice la recuperación de contraseña si es necesario.",
  "requiresHumanReview": false,
  "mode": "traditional"
}
```
 
`mode` acepta `traditional`, `generative` y `ml`. Todos devuelven el mismo formato.
 
| Código | Significado |
|---|---|
| 200 | Análisis correcto |
| 422 | Petición inválida |
| 502 | El motor seleccionado falló o no pudo producir un resultado válido |
 
## 🧪 Pruebas
 
```bash
pytest                    # pruebas unitarias
python -m tests.compare   # comparativa de los tres motores
```
 
Los resultados de la comparativa se guardan en `docs/resultados.md`.
 
## 📚 Documentación

- [Arquitectura](docs/01-arquitectura.md)
- [Contrato](docs/02-contrato.md)
- [Registro de decisiones](docs/03-decisiones.md)
- [Motor de Machine Learning](docs/motor-ml.md)
- [Resultados del motor ML](docs/resultados-ml.md)
- [Resultados de la comparativa](docs/resultados.md)
- [Análisis de resultados](docs/04-analisis.md)

## 🌿 Flujo de trabajo
 
- `main` nunca se toca directamente: todo entra por pull request con la aprobación de un compañero.
- Una rama por módulo: `feat/`, `fix/`, `tests/`, `docs/`, `chore/`.
