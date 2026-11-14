"""API de AI Support Engine: POST /api/analyze.

Referencia: docs/01-arquitectura.md sección 3, docs/02-contrato.md y
decisiones D2 (revisión humana por código) y D4 (502 sin detalles).
"""
import logging
import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.engines import generative, traditional
from app.review import requires_human_review
from app.schemas import AnalyzeRequest, AnalyzeResponse, EngineResult, Mode

load_dotenv()

logger = logging.getLogger(__name__)

ORIGENES_POR_DEFECTO = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
)
HOSTS_LOCALES = {"localhost", "127.0.0.1", "::1"}

# Mensaje fijo: nunca incluye detalles del motor ni del proveedor (D4).
MENSAJE_502 = "El servicio de análisis no está disponible. Intente de nuevo más tarde."

# Se resuelve el motor por módulo en cada petición, no por función guardada.
_MOTORES = {
    Mode.traditional: traditional,
    Mode.generative: generative,
}


def _es_origen_local(origen: str) -> bool:
    try:
        partes = urlparse(origen)
        partes.port  # valida el puerto; lanza ValueError si es inválido
    except ValueError:
        return False
    return (
        partes.scheme in ("http", "https")
        and partes.hostname in HOSTS_LOCALES
        and partes.path in ("", "/")
        and not partes.query
        and not partes.fragment
    )


def origenes_permitidos() -> list[str]:
    """Orígenes CORS leídos de CORS_ORIGINS (separados por comas).

    Solo se aceptan orígenes locales: cualquier otro valor se ignora, incluso
    si viene en la variable de entorno.
    """
    crudo = os.environ.get("CORS_ORIGINS", "")
    if not crudo.strip():
        return list(ORIGENES_POR_DEFECTO)

    origenes = []
    for origen in (parte.strip() for parte in crudo.split(",")):
        if not origen:
            continue
        if _es_origen_local(origen):
            origenes.append(origen.rstrip("/"))
        else:
            logger.warning("Se ignoró un origen CORS que no es local.")
    return origenes


app = FastAPI(title="AI Support Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origenes_permitidos(),
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


def _llamar_motor(mode: Mode, message: str) -> EngineResult | None:
    """Devuelve el resultado del motor, o None si el motor lanzó cualquier
    excepción.

    Del fallo solo se registra el nombre del motor y la clase de la
    excepción. Nunca su mensaje, su traceback ni su causa (__cause__): pueden
    traer detalles internos o la API key.
    """
    try:
        return _MOTORES[mode].analyze(message)
    except Exception as exc:
        logger.error("El motor %s falló con %s.", mode.value, type(exc).__name__)
        return None


class ErrorResponse(BaseModel):
    """Cuerpo de las respuestas de error: solo el campo detail."""

    detail: str


@app.post(
    "/api/analyze",
    response_model=AnalyzeResponse,
    responses={
        502: {
            "model": ErrorResponse,
            "description": "El motor no pudo procesar la solicitud",
        }
    },
)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    result = _llamar_motor(request.mode, request.message)
    if result is None:
        raise HTTPException(status_code=502, detail=MENSAJE_502)

    return AnalyzeResponse(
        **result.model_dump(),
        requiresHumanReview=requires_human_review(request.message, result),
        mode=request.mode,
    )
