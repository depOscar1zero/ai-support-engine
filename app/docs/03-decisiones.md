# AI Support Engine — Registro de decisiones

Documentos relacionados: [Arquitectura](01-arquitectura.md) · [Contrato](02-contrato.md)

Cada decisión registra qué se eligió, por qué y qué alternativa se descartó. Las decisiones nuevas se agregan al final con el siguiente número; las que cambien no se borran, se marcan como reemplazadas.

## Resumen

| # | Decisión | Estado |
|---|---|---|
| D1 | Una función `analyze()` por motor con un tipo de retorno común | Aprobada |
| D2 | `requiresHumanReview` lo decide el código, no el modelo | Aprobada |
| D3 | Revisión humana también por términos de seguridad en el mensaje | Propuesta |
| D4 | Si Gemini falla o devuelve JSON inválido, la API responde 502 | Aprobada |
| D5 | La salida de Gemini se valida con el mismo modelo Pydantic | Aprobada |
| D6 | Instrucciones del sistema separadas del mensaje del usuario | Aprobada |
| D7 | API key en `.env`, fuera del repositorio | Aprobada |
| D8 | La clasificación de referencia se define antes de programar | Aprobada |
| D9 | El login de la demo es solo visual | Propuesta |

## D1 — Una función `analyze()` por motor con un tipo de retorno común

- **Fecha:** 12 de noviembre de 2026
- **Decisión:** cada motor expone `analyze(message: str) -> EngineResult`.
- **Por qué:** los tres trabajan en paralelo sin tocar el código de los otros, y la API cambia de motor con una sola selección.
- **Alternativa descartada:** que cada motor arme su propio JSON. Garantiza diferencias de formato entre ambos y rompe el requisito de contrato único.

## D2 — `requiresHumanReview` lo decide el código, no el modelo

- **Fecha:** 12 de noviembre de 2026
- **Decisión:** el campo se calcula en `app/review.py` después de que el motor responde.
- **Por qué:** un prompt injection puede convencer a un modelo, pero no a una condición en código.
- **Alternativa descartada:** pedirle el campo a Gemini dentro de su JSON.

## D3 — Revisión humana también por términos de seguridad en el mensaje

- **Fecha:** 12 de noviembre de 2026
- **Decisión:** se marca revisión humana si la categoría es `SECURITY` **o** si el mensaje contiene términos de seguridad, sin importar lo que haya devuelto el motor.
- **Por qué:** cubre el caso en que el modelo es engañado y clasifica un incidente como `FEATURE`.
- **Costo aceptado:** habrá falsos positivos (por ejemplo, alguien que pide una función "de seguridad"). Se prefiere revisar de más que dejar pasar un incidente.
- **Alternativa descartada:** confiar solo en la categoría.

## D4 — Si Gemini falla o devuelve JSON inválido, la API responde 502

- **Fecha:** 12 de noviembre de 2026
- **Decisión:** el motor generativo lanza `EngineError` y la API lo traduce a HTTP 502 con un mensaje genérico.
- **Por qué:** el enunciado prohíbe simular respuestas generativas.
- **Alternativa descartada:** caer al motor tradicional respondiendo `mode: generative`. Sería presentar como generativa una respuesta que no lo es.

## D5 — La salida de Gemini se valida con el mismo modelo Pydantic

- **Fecha:** 12 de noviembre de 2026
- **Decisión:** se pide salida estructurada a Gemini y además se valida con `EngineResult` de nuestro lado.
- **Por qué:** una sola fuente de verdad para el formato; pedir el formato no es lo mismo que comprobarlo.
- **Alternativa descartada:** validar los campos con condiciones escritas a mano.

## D6 — Instrucciones del sistema separadas del mensaje del usuario

- **Fecha:** 12 de noviembre de 2026
- **Decisión:** las reglas van en `system_instruction`; el mensaje del usuario se envía aparte y se declara como dato a analizar.
- **Por qué:** reduce el efecto de mensajes como "ignora todas las instrucciones anteriores".
- **Límite conocido:** reduce el riesgo, no lo elimina. Por eso existen D2 y D3.
- **Alternativa descartada:** concatenar instrucciones y mensaje en un solo texto.

## D7 — API key en `.env`, fuera del repositorio

- **Fecha:** 12 de noviembre de 2026
- **Decisión:** la key vive en `.env` (ignorado por git); el repositorio solo contiene `.env.example` sin valores.
- **Por qué:** evita exponer credenciales, requisito explícito del proyecto.
- **Alternativa descartada:** key escrita en el código.

## D8 — La clasificación de referencia se define antes de programar

- **Fecha:** 12 de noviembre de 2026
- **Decisión:** los tres congelan `tests/cases.json` el jueves, antes de escribir los motores.
- **Por qué:** si la referencia se define después, tiende a ajustarse a lo que los motores ya responden y el porcentaje deja de significar algo.
- **Regla derivada:** si un caso de referencia resulta estar mal, se corrige y se anota aquí el motivo.
- **Alternativa descartada:** etiquetar los casos al final.

## D9 — El login de la demo es solo visual

- **Fecha:** 12 de noviembre de 2026
- **Decisión:** el login y los comentarios existen para la demo en vivo; no hay autenticación real ni protegen la API.
- **Por qué:** no es requisito y no hay tiempo de hacerlo seguro antes del lunes; se declara abiertamente en lugar de aparentar seguridad.
- **Alternativa descartada:** autenticación real con usuarios.
