# Demo web

Demo de AI Support Engine en HTML, CSS y JavaScript, sin dependencias ni paso
de build. La sirve la propia API en `/`:

```bash
python -m uvicorn app.main:app --port 8000
```

Después abre <http://localhost:8000/>. Si abres `index.html` desde otro
servidor (por ejemplo Live Server), la página no encontrará la API: usa la
dirección anterior.

El inicio de sesión es solo visual (decisión D9): acepta cualquier valor, no
guarda nada y no protege la API.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `index.html` | Estructura de la página |
| `styles.css` | Todo el aspecto visual. Colores, tipografías y espaciados son variables al inicio del archivo |
| `app.js` | Lógica: login visual, formulario, llamada a `/api/analyze`, resultado, historial y estados |

## Qué puede cambiar libremente quien aplique el diseño

- **Todo `styles.css`**: variables, reglas, clases, animaciones y responsive.
- **La estructura visual de `index.html`**: orden de las secciones, contenedores,
  textos, títulos, iconos o imágenes, y las clases CSS.

## Qué no debe tocar

- **Los `id` del HTML que usa `app.js`** (por ejemplo `login-form`, `message-input`,
  `char-counter`, `mode-select`, `submit-button`, `loading-indicator`,
  `error-message`, `result-category`, `result-priority`, `result-response`,
  `result-mode`, `review-warning`, `history-list`, `history-empty`). Puede mover
  el elemento donde quiera, pero cada `id` debe seguir existiendo una sola vez.
- **El atributo `hidden`** de los elementos que lo traen: `app.js` lo activa y lo
  quita para mostrar u ocultar pantallas y avisos.
- **Los atributos `data-example-message`** de los botones de ejemplo: contienen
  los mensajes de los casos 1, 5, 7 y 11 de `tests/cases.json`, y un test
  comprueba que coinciden.
- **El `maxlength="2000"` del mensaje**: es el límite del contrato.
- **La lógica de `app.js`**. No inserta HTML (usa `textContent`) ni genera
  estilos: cambia solo atributos (`hidden`, `disabled`, `data-category`,
  `data-priority`, `data-state`, `data-review`) y `styles.css` decide cómo se ve
  cada uno. Conviene mantenerlo así.

Hay tests que vigilan estas reglas (`tests/test_frontend.py`).

## Seguridad

No hay claves ni secretos en el frontend: el navegador solo llama a la API.
