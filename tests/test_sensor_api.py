"""Endpoint tests for sensor ingestion, including malformed payloads."""

import asyncio
from collections.abc import Generator

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from database.base import Base
from database.connection import get_db_session
from database.models import SensorReading

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, expire_on_commit=False)


def override_db_session() -> Generator[Session, None, None]:
    with TestSession() as session:
        yield session


def post_sensor(payload: dict[str, object]) -> Response:
    async def send_request() -> Response:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.post("/sensor-data", json=payload)

    return asyncio.run(send_request())


def post_raw_sensor(body: str) -> Response:
    async def send_request() -> Response:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.post(
                "/sensor-data",
                content=body,
                headers={"content-type": "application/json"},
            )

    return asyncio.run(send_request())


@pytest.fixture(autouse=True)
def database() -> Generator[None, None, None]:
    Base.metadata.create_all(test_engine)
    app.dependency_overrides[get_db_session] = override_db_session
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)


def test_sensor_data_is_validated_and_stored() -> None:
    response = post_sensor(
        {
            "device_id": "sensor-001",
            "temperature": 28.5,
            "humidity": 71.2,
            "timestamp": "2026-09-19T10:30:00Z",
        }
    )

    assert response.status_code == 201
    assert response.json() == {
        "success": True,
        "message": "Sensor data stored successfully",
        "data": {"id": 1},
    }

    with TestSession() as session:
        reading = session.scalar(select(SensorReading))
        assert reading is not None
        assert reading.device_id == "sensor-001"
        assert reading.recorded_at is not None
        assert reading.created_at is not None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("device_id", "   "),
        ("temperature", "28.5"),
        ("humidity", -0.1),
        ("humidity", 100.1),
        ("timestamp", "not-a-timestamp"),
    ],
)
def test_malformed_sensor_payload_is_rejected(field: str, value: object) -> None:
    payload: dict[str, object] = {
        "device_id": "sensor-001",
        "temperature": 28.5,
        "humidity": 71.2,
        "timestamp": "2026-09-19T10:30:00Z",
    }
    payload[field] = value

    response = post_sensor(payload)

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]


def test_unknown_sensor_field_is_rejected() -> None:
    response = post_sensor(
        {
            "device_id": "sensor-001",
            "temperature": 28.5,
            "humidity": 71.2,
            "timestamp": "2026-09-19T10:30:00Z",
            "unexpected": "value",
        }
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "body.unexpected"


def test_malformed_json_uses_consistent_error_envelope() -> None:
    response = post_raw_sensor('{"device_id":')

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
