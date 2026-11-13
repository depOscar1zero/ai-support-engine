# AI Support Engine — Arquitectura

**Equipo:** Alejandro Contreras Martínez · Lilia Tun Hernández · Oscar Espinoza Landeta
**Fecha:** 12 de noviembre de 2026 · **Entrega:** lunes 16 de noviembre de 2026

Documentos relacionados: [Contrato](02-contrato.md) · [Registro de decisiones](03-decisiones.md)

## 1. Qué construimos y por qué

Una empresa recibe 3,000 solicitudes de soporte al día y una persona las lee, clasifica, prioriza y responde a mano. Construimos un prototipo que automatiza esa primera pasada con dos motores intercambiables, para comparar qué tan bien lo hace cada uno:

- **Motor tradicional:** reglas y condiciones en Python, sin modelo generativo.
- **Motor generativo:** Gemini 3.8 Flash mediante API (`gemini-3.8-flash`).

Se califica el repositorio, una demo en vivo y la evidencia de decisiones en `docs/`.

## 2. Alcance

**Objetivos**
- `POST /api/analyze` funcional con `mode` = `traditional` | `generative`.
- Ambos motores cumplen el mismo contrato de respuesta.
- Validación de entrada, manejo de errores del proveedor y verificación del formato generativo.
- Revisión humana obligatoria para posibles incidentes de seguridad.
- Comparativa con 10+ solicitudes y porcentaje de aciertos por motor.
- Interfaz de demo (login, formulario, comentarios) para la presentación en vivo.

**Fuera de alcance**
- Autenticación real: el login de la demo es solo visual y no protege la API.
- Base de datos o persistencia de solicitudes.
- Despliegue en la nube: la demo corre en local.

**Lo que haría fallar el proyecto aunque "funcione"**
- Respuestas generativas simuladas o escritas a mano.
- Una API key dentro del repositorio.
- Que un mensaje malicioso logre bajar la prioridad o apagar la revisión humana de un incidente de seguridad.

## 3. Flujo de una solicitud

```
Cliente (demo web / curl)
        │  POST /api/analyze {message, mode}
        ▼
   app/main.py ── valida con Pydantic (422 si es inválido)
        │
        ├─ mode=traditional → engines/traditional.py ─┐
        └─ mode=generative  → engines/generative.py ──┤→ EngineResult
                                   │ (Gemini API)      │
                                   ▼                   ▼
                          error o JSON inválido   app/review.py
                               → HTTP 502        (requiresHumanReview)
                                                       ▼
                                                AnalyzeResponse
```

## 4. Componentes

| Componente | Responsabilidad | Responsable |
|---|---|---|
| `app/schemas.py` | Contrato compartido de entrada y salida | Oscar |
| `app/main.py` | Endpoint, validación, selección de motor, traducción de errores a HTTP | Oscar |
| `app/review.py` | Decide `requiresHumanReview` con reglas de código | Oscar |
| `app/engines/traditional.py` | Clasificación por reglas, sin red ni modelo | Alejandro |
| `app/engines/generative.py` | Llamada a Gemini y verificación de su salida | Lilia (con apoyo de Oscar) |
| `frontend/` | Demo visual | Lilia (diseño) · Oscar (conexión) |
| `tests/` | Casos de referencia y comparativa | Oscar, con casos definidos por los tres |

## 5. Estructura del repositorio

```
app/
  schemas.py
  main.py
  review.py
  engines/
    __init__.py       define EngineError
    traditional.py
    generative.py
frontend/
tests/
  cases.json          casos con clasificación de referencia
  compare.py          ejecuta ambos motores y calcula el %
docs/
.env.example          nombres de variables, sin valores reales
.gitignore            incluye .env
requirements.txt
```

## 6. Calendario

| Día | Qué pasa |
|---|---|
| Jueves 12 | Oscar sube estructura y `schemas.py` a `main`. Los tres congelan `cases.json`. |
| Viernes 13 – Sábado 14 | Cada quien en su rama. Oscar acompaña a Lilia el viernes con Gemini. |
| Domingo 15 | Integración, `compare.py`, `docs/resultados.md`, conexión del frontend. |
| Lunes 16 | Colchón, ensayo de la demo y entrega. |

## 7. Riesgos

| Riesgo | Mitigación |
|---|---|
| Lilia lleva diseño visual y motor generativo a la vez | Oscar la acompaña el viernes; la demo usa un formulario simple si el diseño completo no llega |
| Límite de peticiones del nivel gratuito de Gemini | `compare.py` pausa entre llamadas; no correr la comparativa minutos antes de la demo |
| Falla de internet o de Gemini durante la demo | Tener `docs/resultados.md` y capturas listas; el modo `traditional` funciona sin red |
| Ramas que chocan el domingo | Cada quien solo toca sus archivos; integración el domingo temprano, no en la noche |
