"""Motor tradicional: clasificación por reglas, sin red ni modelo."""

import re
import unicodedata

from app.schemas import Category, EngineResult, Priority


# El orden también define la precedencia cuando dos categorías empatan.
PRECEDENCIA = (
    Category.SECURITY,
    Category.ACCESS,
    Category.BUG,
    Category.FEATURE,
)

class Raiz(str):
    """Término que coincide con cualquier palabra que empiece con este texto.

    Un término normal (str) es una palabra o frase completa con plural
    opcional. Una Raíz exige límite de palabra al inicio y admite cualquier
    terminación.
    """


REGLAS = {
    Category.SECURITY: {
        "vulnerabilidad": 3,
        "brecha": 3,
        Raiz("hacke"): 3,
        "hackeo": 3,
        "filtracion": 3,
        "filtraciones": 3,
        "filtraron": 3,
        "se filtro": 3,
        "se filtra": 3,
        "se filtran": 3,
        "filtrando": 3,
        "filtrado": 3,
        "filtrados": 3,
        "phishing": 3,
        "sospechoso": 2,
        "acceso no autorizado": 3,
        "datos de otros": 3,
        "de otros clientes": 3,
        "alguien cambio": 3,
        "cambio mi contrasena": 3,
    },
    Category.ACCESS: {
        "iniciar sesion": 3,
        "contrasena": 2,
        "login": 3,
        "no puedo entrar": 3,
        Raiz("bloquead"): 2,
        "acceso": 1,
    },
    Category.BUG: {
        "error": 2,
        "falla": 2,
        Raiz("se cierr"): 3,
        "no funciona": 2,
        "no carga": 2,
        "se congela": 3,
        "no hace nada": 2,
    },
    Category.FEATURE: {
        "seria util": 3,
        "pueden agregar": 3,
        "me gustaria": 2,
        "sugerencia": 2,
        "nueva funcion": 3,
    },
}

# Una coincidencia de peso 3 representa una señal fuerte de seguridad. Ante
# una de estas señales, SECURITY prevalece aunque otra categoría sume más.
TERMINOS_SEGURIDAD_FUERTES = tuple(
    termino for termino, peso in REGLAS[Category.SECURITY].items() if peso == 3
)

PRIORIDAD_BASE = {
    Category.SECURITY: Priority.HIGH,
    Category.ACCESS: Priority.MEDIUM,
    Category.BUG: Priority.MEDIUM,
    Category.FEATURE: Priority.LOW,
}

MODIFICADORES_PRIORIDAD = {
    Category.SECURITY: (
        "filtracion",
        "filtraciones",
        "filtraron",
        "se filtro",
        "se filtra",
        "se filtran",
        "filtrando",
        "filtrado",
        "filtrados",
        "datos de otros",
        "de otros clientes",
        "todos los usuarios",
    ),
    Category.BUG: (Raiz("se cierr"), Raiz("perdi"), "no puedo trabajar"),
    Category.ACCESS: ("todos", "urgente", "nadie puede"),
    Category.FEATURE: (),
}

RESPUESTAS = {
    Category.ACCESS: (
        "Lamentamos el inconveniente. Verifique sus credenciales y utilice la "
        "recuperación de contraseña si es necesario."
    ),
    Category.BUG: (
        "Gracias por reportarlo. Registramos el fallo y nuestro equipo técnico "
        "lo está revisando."
    ),
    Category.FEATURE: (
        "Gracias por su sugerencia. La compartimos con el equipo de producto "
        "para evaluarla."
    ),
    Category.SECURITY: (
        "Gracias por avisar. Su reporte fue escalado al equipo de seguridad "
        "para revisión inmediata."
    ),
}


def normalizar(texto: str) -> str:
    """Convierte a minúsculas y elimina marcas diacríticas."""
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )


def clasificar(texto: str) -> Category:
    """Suma los pesos de cada coincidencia y resuelve empates por precedencia."""
    if any(
        _buscar_termino(termino, texto)
        for termino in TERMINOS_SEGURIDAD_FUERTES
    ):
        return Category.SECURITY

    puntuaciones = {
        categoria: _puntuar_sin_solapamientos(texto, REGLAS[categoria])
        for categoria in PRECEDENCIA
    }

    mayor_puntuacion = max(puntuaciones.values())
    if mayor_puntuacion == 0:
        return Category.BUG

    return next(
        categoria
        for categoria in PRECEDENCIA
        if puntuaciones[categoria] == mayor_puntuacion
    )


def _puntuar_sin_solapamientos(texto: str, reglas: dict[str, int]) -> int:
    """Suma coincidencias distintas, sin contar dos frases superpuestas."""
    coincidencias = []
    for termino, peso in reglas.items():
        coincidencia = _buscar_termino(termino, texto)
        if coincidencia:
            coincidencias.append((coincidencia.start(), coincidencia.end(), peso))

    # Las frases más largas representan mejor una sola señal compuesta.
    coincidencias.sort(
        key=lambda coincidencia: coincidencia[1] - coincidencia[0],
        reverse=True,
    )
    seleccionadas = []
    puntuacion = 0
    for inicio, fin, peso in coincidencias:
        if any(
            inicio < otro_fin and otro_inicio < fin
            for otro_inicio, otro_fin in seleccionadas
        ):
            continue
        seleccionadas.append((inicio, fin))
        puntuacion += peso

    return puntuacion


def _buscar_termino(termino: str, texto: str):
    """Busca un término en el texto.

    Término exacto: palabra completa con plural opcional.
    Raíz: límite de palabra al inicio y cualquier terminación.
    """
    if isinstance(termino, Raiz):
        return re.search(rf"\b{re.escape(termino)}\w*", texto)
    return re.search(rf"\b{re.escape(termino)}(?:s|es)?\b", texto)


def priorizar(texto: str, category: Category) -> Priority:
    """Aplica la prioridad base y los modificadores definidos para la categoría."""
    if any(
        _buscar_termino(termino, texto)
        for termino in MODIFICADORES_PRIORIDAD[category]
    ):
        if category is Category.SECURITY:
            return Priority.CRITICAL
        if category in (Category.ACCESS, Category.BUG):
            return Priority.HIGH

    return PRIORIDAD_BASE[category]


def analyze(message: str) -> EngineResult:
    """Clasifica un mensaje y devuelve el resultado definido por el contrato."""
    texto = normalizar(message)
    category = clasificar(texto)
    priority = priorizar(texto, category)
    return EngineResult(
        category=category,
        priority=priority,
        response=RESPUESTAS[category],
    )
