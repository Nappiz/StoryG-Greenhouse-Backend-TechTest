"""Shared schema field types."""

from typing import Annotated

from pydantic import StringConstraints

DeviceId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
]
