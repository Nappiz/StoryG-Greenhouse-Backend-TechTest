"""Schemas for backend dependency health reporting."""

from typing import Literal

from pydantic import BaseModel


class ServiceStatuses(BaseModel):
    """Status of the backend and each external dependency."""

    backend: Literal["up"] = "up"
    database: Literal["connected", "disconnected"]
    mqtt: Literal["connected", "disconnected"]


class HealthResponse(BaseModel):
    """Overall health derived from live dependency checks."""

    status: Literal["healthy", "degraded"]
    services: ServiceStatuses
