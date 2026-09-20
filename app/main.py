"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.device import router as device_router
from api.health import router as health_router
from api.sensor import router as sensor_router
from core.config import get_settings
from core.exceptions import ApplicationError
from mqtt.client import MQTTClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Keep one MQTT client alive for the complete application lifecycle."""
    settings = get_settings()
    mqtt_client = MQTTClient(settings.mqtt_host, settings.mqtt_port)
    application.state.mqtt_client = mqtt_client
    mqtt_client.start()
    try:
        yield
    finally:
        mqtt_client.stop()


app = FastAPI(
    title="Greenhouse IoT Backend",
    description="Backend API for greenhouse sensor ingestion and device control.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(sensor_router)
app.include_router(device_router)
app.include_router(health_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return the stable validation error envelope from the API contract."""
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": details,
            },
        },
    )


@app.exception_handler(ApplicationError)
async def application_exception_handler(
    _request: Request,
    exc: ApplicationError,
) -> JSONResponse:
    """Return safe messages for expected service and dependency failures."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    _request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Keep framework-generated HTTP errors inside the common envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
            },
        },
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Log internal details while returning a non-sensitive response."""
    logger.error(
        "Unhandled application error for %s %s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
            },
        },
    )


@app.get("/", tags=["System"])
async def root() -> dict[str, str]:
    """Return a lightweight confirmation that the API process is running."""
    return {"message": "Greenhouse IoT Backend is running"}
