# Motor tradicional

El motor tradicional implementa `analyze(message: str) -> EngineResult` mediante
reglas deterministas. No utiliza modelos generativos ni realiza peticiones de red.

## Normalización

Antes de evaluar las reglas, el mensaje se convierte a minúsculas y se eliminan
los acentos mediante normalización Unicode. De esta forma, por ejemplo, `sesión`
y `sesion` producen la misma coincidencia. Los términos se buscan como palabras
o frases completas para evitar coincidencias accidentales dentro de otras
palabras. La búsqueda también acepta los sufijos regulares de plural `s` y `es`.

## Clasificación y puntuación

Cada categoría (`SECURITY`, `ACCESS`, `BUG` y `FEATURE`) tiene términos con un
peso. Cada término encontrado suma su peso a la categoría correspondiente y la
categoría con mayor puntuación es el resultado.

Si varias categorías obtienen la misma puntuación, se usa esta precedencia:

1. `SECURITY`
2. `ACCESS`
3. `BUG`
4. `FEATURE`

La precedencia favorece el tratamiento de un posible incidente de seguridad
frente a una solicitud de acceso, un fallo o una sugerencia.

Además, una señal fuerte de seguridad prevalece aunque otra categoría acumule
más puntos. Las coincidencias solapadas dentro de una categoría se consideran
una sola señal y se conserva la frase más larga, evitando puntuar dos veces una
misma expresión compuesta.

Si ningún término coincide, el motor devuelve `BUG` con prioridad `MEDIUM`.
Este comportamiento predeterminado es una limitación conocida del enfoque.

## Prioridad

Cada categoría parte de una prioridad base:

| Categoría | Prioridad base |
|---|---|
| `SECURITY` | `HIGH` |
| `ACCESS` | `MEDIUM` |
| `BUG` | `MEDIUM` |
| `FEATURE` | `LOW` |

Las formas completas de filtración (incluidas formas en presente, participios y
plurales) o los términos de exposición general suben `SECURITY` a
`CRITICAL`. Los fallos que cierran la aplicación, provocan pérdida o impiden
trabajar suben `BUG` a `HIGH`. Los problemas de acceso generales o urgentes
suben `ACCESS` a `HIGH`. `FEATURE` permanece en `LOW`.

`SECURITY` nunca tiene una prioridad inferior a `HIGH`, aunque el mensaje pida
explícitamente clasificarlo con prioridad baja.

## Respuestas

Cada categoría devuelve una respuesta fija, profesional y en español. El motor
no genera texto dinámico y no calcula `requiresHumanReview`; esa responsabilidad
pertenece a la API.

## Limitaciones

El motor depende de coincidencias textuales. Puede no reconocer sinónimos que no
estén incluidos, errores de escritura, expresiones nuevas, negaciones o sarcasmo.
Tampoco interpreta el contexto con la flexibilidad de un modelo de lenguaje.
