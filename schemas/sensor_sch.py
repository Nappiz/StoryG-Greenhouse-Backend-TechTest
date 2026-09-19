"""Schemas for sensor ingestion."""

from typing import Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from schemas.common import DeviceId


class SensorDataRequest(BaseModel):
    """Validated payload accepted by POST /sensor-data."""

    model_config = ConfigDict(extra="forbid")

    device_id: DeviceId
    temperature: float = Field(allow_inf_nan=False)
    humidity: float = Field(ge=0, le=100, allow_inf_nan=False)
    timestamp: AwareDatetime

    @field_validator("temperature", "humidity", mode="before")
    @classmethod
    def require_json_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Input should be a number")
        return value


class StoredSensorData(BaseModel):

    id: int = Field(gt=0)


class SensorDataResponse(BaseModel):

    success: Literal[True] = True
    message: Literal["Sensor data stored successfully"] = (
        "Sensor data stored successfully"
    )
    data: StoredSensorData
