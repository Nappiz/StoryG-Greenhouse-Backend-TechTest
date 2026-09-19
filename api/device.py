"""Device-control API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from api.dependencies import get_mqtt_client
from mqtt.client import MQTTClient
from schemas.device_sch import DeviceControlRequest, DeviceControlResponse
from schemas.error_sch import ErrorResponse
from services.device_service import DeviceService


router = APIRouter(tags=["Devices"])


def get_device_service(
    mqtt_client: Annotated[MQTTClient, Depends(get_mqtt_client)],
) -> DeviceService:
    """Build a device service using the lifecycle-managed MQTT client."""
    return DeviceService(mqtt_client)


@router.post(
    "/device-control",
    response_model=DeviceControlResponse,
    status_code=status.HTTP_200_OK,
    responses={
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def control_device(
    payload: DeviceControlRequest,
    service: Annotated[DeviceService, Depends(get_device_service)],
) -> DeviceControlResponse:
    """Validate and publish one ON/OFF command with QoS 1."""
    return service.send_command(payload)
