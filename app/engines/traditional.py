"""Motor tradicional: clasificación por reglas, sin red ni modelo."""

import unicodedata

from app.schemas import Category, EngineResult, Priority


# El orden también define la precedencia cuando dos categorías empatan.
PRECEDENCIA = (
    Category.SECURITY,
    Category.ACCESS,
    Category.BUG,
    Category.FEATURE,
)

REGLAS = {
    Category.SECURITY: {
        "vulnerabilidad": 3,
        "hackea": 3,
        "filtr": 3,
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
        "bloquead": 2,
        "acceso": 1,
    },
    Category.BUG: {
        "error": 2,
        "falla": 2,
        "se cierra": 3,
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

PRIORIDAD_BASE = {
    Category.SECURITY: Priority.HIGH,
    Category.ACCESS: Priority.MEDIUM,
    Category.BUG: Priority.MEDIUM,
    Category.FEATURE: Priority.LOW,
}

MODIFICADORES_PRIORIDAD = {
    Category.SECURITY: ("filtr", "datos de otros", "de otros clientes", "todos los usuarios"),
    Category.BUG: ("se cierra", "perdi", "no puedo trabajar"),
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
    puntuaciones = {
        categoria: sum(
            peso for termino, peso in REGLAS[categoria].items() if termino in texto
        )
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


def priorizar(texto: str, category: Category) -> Priority:
    """Aplica la prioridad base y los modificadores definidos para la categoría."""
    if any(termino in texto for termino in MODIFICADORES_PRIORIDAD[category]):
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
