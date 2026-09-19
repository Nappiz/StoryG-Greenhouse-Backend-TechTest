"""Backend dependency health endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends

from api.dependencies import get_mqtt_client
from database.connection import check_database_connection
from mqtt.client import MQTTClient
from schemas.health_sch import HealthResponse
from services.health_service import HealthService


router = APIRouter(tags=["System"])


def get_health_service(
    mqtt_client: Annotated[MQTTClient, Depends(get_mqtt_client)],
) -> HealthService:
    """Build the health service with live dependency probes."""
    return HealthService(check_database_connection, mqtt_client)


@router.get("/status", response_model=HealthResponse)
def get_status(
    service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthResponse:
    """Report actual PostgreSQL and MQTT connection status."""
    return service.get_status()
