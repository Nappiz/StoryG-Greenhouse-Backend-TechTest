"""Consistent API error response schemas."""

from typing import Literal

from pydantic import BaseModel


class ErrorDetail(BaseModel):

    field: str
    message: str
    type: str


class ErrorBody(BaseModel):

    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):

    success: Literal[False] = False
    error: ErrorBody
