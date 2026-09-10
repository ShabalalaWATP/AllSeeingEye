"""Canonical spatial scope frozen in collection plans; never a display envelope."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from ase.domain.research_area import (
    ResearchArea,
    area_from_dict,
    area_to_dict,
    direct_area_from_geometry,
)


class ResearchAreaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    geometry: dict[str, Any]
    _area: ResearchArea = PrivateAttr()

    @model_validator(mode="after")
    def validate_geometry(self) -> "ResearchAreaIn":
        self._area = direct_area_from_geometry(self.geometry)
        return self

    def to_domain(self) -> ResearchArea:
        return self._area


class ResearchAreaOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    geometry: dict[str, Any]
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="before")
    @classmethod
    def canonical(cls, value: Any) -> Any:
        if isinstance(value, ResearchArea):
            return area_to_dict(value)
        return area_to_dict(area_from_dict(value))
