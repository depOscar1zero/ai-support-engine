"""Contrato compartido de entrada y salida.

Referencia: docs/02-contrato.md, sección 3. Nadie cambia este archivo sin
avisar a los otros dos integrantes del equipo.
"""
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Category(str, Enum):
    ACCESS = "ACCESS"
    BUG = "BUG"
    FEATURE = "FEATURE"
    SECURITY = "SECURITY"


class Priority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Mode(str, Enum):
    traditional = "traditional"
    generative = "generative"


class AnalyzeRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    mode: Mode

    @field_validator("message")
    @classmethod
    def no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message no puede estar vacío")
        return v


class EngineResult(BaseModel):
    category: Category
    priority: Priority
    response: str = Field(min_length=1)


class AnalyzeResponse(EngineResult):
    requiresHumanReview: bool
    mode: Mode
