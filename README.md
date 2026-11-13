# 🤖 AI Support Engine
 
Prototipo de clasificación inteligente de solicitudes de soporte. Compara dos enfoques sobre el mismo contrato de API:
 
- **Motor tradicional:** reglas y condiciones en Python, sin modelo generativo.
- **Motor generativo:** Gemini 3.8 Flash mediante API.
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
frontend/             demo visual
tests/
  cases.json          casos con clasificación de referencia
  compare.py          comparativa de ambos motores
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
GEMINI_MODEL=gemini-3.8-flash
```
 
El archivo `.env` está ignorado por git. **Nunca subas la key al repositorio.**
 
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
 
`mode` acepta `traditional` y `generative`. Ambos devuelven el mismo formato.
 
| Código | Significado |
|---|---|
| 200 | Análisis correcto |
| 422 | Petición inválida |
| 502 | El motor generativo falló o devolvió un formato inválido |
 
## 🧪 Pruebas
 
```bash
pytest                    # pruebas unitarias
python -m tests.compare   # comparativa de ambos motores
```
 
Los resultados de la comparativa se guardan en `docs/resultados.md`.
 
## 📚 Documentación
 
- [Arquitectura](docs/01-arquitectura.md)
- [Contrato](docs/02-contrato.md)
- [Registro de decisiones](docs/03-decisiones.md)
## 🌿 Flujo de trabajo
 
- `main` nunca se toca directamente: todo entra por pull request con la aprobación de un compañero.
- Una rama por módulo: `feat/`, `fix/`, `tests/`, `docs/`, `chore/`.