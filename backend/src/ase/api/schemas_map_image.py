"""Manually parsed schema, after authenticated bounded map-image intake."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ase.application.ports.map_image import MAX_MAP_IMAGE_BYTES, MapImageOptions


class MapImagePackageIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    png_base64: str = Field(min_length=1, max_length=4 * ((MAX_MAP_IMAGE_BYTES + 2) // 3))
    include_annotations: bool = False
    use_basis: Literal["standard", "noncommercial", "licensed"] = "standard"
    permitted_use: str = Field(default="", max_length=1000)

    @field_validator("permitted_use")
    @classmethod
    def plain_statement(cls, value: str) -> str:
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("Use a plain permitted-use statement without control characters.")
        return value.strip()

    def to_options(self) -> MapImageOptions:
        return MapImageOptions(**self.model_dump())
