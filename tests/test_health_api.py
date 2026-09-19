"""Tests for healthy and degraded dependency reporting."""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.exc import SQLAlchemyError

from api.health import get_health_service
from app.main import app
from services.health_service import HealthService


class MQTTState:
    def __init__(self, status: str) -> None:
        self.status = status


def get_status() -> Response:
    async def send_request() -> Response:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.get("/status")

    return asyncio.run(send_request())


@pytest.fixture(autouse=True)
def clear_dependencies() -> None:
    yield
    app.dependency_overrides.clear()


def test_status_is_healthy_when_dependencies_are_available() -> None:
    service = HealthService(lambda: None, MQTTState("connected"))  # type: ignore[arg-type]
    app.dependency_overrides[get_health_service] = lambda: service

    response = get_status()

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "services": {
            "backend": "up",
            "database": "connected",
            "mqtt": "connected",
        },
    }


def test_status_is_degraded_when_mqtt_is_disconnected() -> None:
    service = HealthService(lambda: None, MQTTState("disconnected"))  # type: ignore[arg-type]
    app.dependency_overrides[get_health_service] = lambda: service

    response = get_status()

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["services"]["mqtt"] == "disconnected"


def test_status_is_degraded_when_database_is_disconnected() -> None:
    def failed_database_check() -> None:
        raise SQLAlchemyError("database unavailable")

    service = HealthService(
        failed_database_check,
        MQTTState("connected"),  # type: ignore[arg-type]
    )
    app.dependency_overrides[get_health_service] = lambda: service

    response = get_status()

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["services"]["database"] == "disconnected"
