"""Motor tradicional: clasificación por reglas, sin red ni modelo.

Pendiente de implementar. Contrato: docs/02-contrato.md, sección 2. Si no
puede entregar un EngineResult válido, debe lanzar EngineError.
"""
from app.schemas import EngineResult


def analyze(message: str) -> EngineResult:
    raise NotImplementedError("Motor tradicional pendiente de implementar")
