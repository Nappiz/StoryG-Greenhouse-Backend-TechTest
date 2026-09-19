"""Schemas for greenhouse device control."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from schemas.common import DeviceId


class DeviceControlRequest(BaseModel):
    """Validated command accepted by POST /device-control."""

    model_config = ConfigDict(extra="forbid")

    device_id: DeviceId
    command: Literal["ON", "OFF"]


class PublishedDeviceCommand(BaseModel):

    device_id: str
    command: Literal["ON", "OFF"]


class DeviceControlResponse(BaseModel):

    success: Literal[True] = True
    message: Literal["Device control command published successfully"] = (
        "Device control command published successfully"
    )
    data: PublishedDeviceCommand
