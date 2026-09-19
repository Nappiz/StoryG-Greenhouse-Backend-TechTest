"""Tests for the initial FastAPI application foundation."""

import asyncio

from httpx import ASGITransport, AsyncClient, Response

from app.main import app


def get(path: str) -> Response:
    """Issue an in-process HTTP GET without starting a network server."""

    async def send_request() -> Response:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.get(path)

    return asyncio.run(send_request())


def test_root_returns_running_message() -> None:
    response = get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Greenhouse IoT Backend is running"}


def test_swagger_ui_is_available() -> None:
    response = get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()


def test_openapi_schema_is_available() -> None:
    response = get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Greenhouse IoT Backend"


def test_unknown_route_uses_consistent_error_envelope() -> None:
    response = get("/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "error": {
            "code": "HTTP_ERROR",
            "message": "Not Found",
        },
    }
