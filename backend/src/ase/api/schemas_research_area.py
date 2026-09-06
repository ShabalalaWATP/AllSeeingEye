"""Canonical spatial scope frozen in collection plans; never a display envelope."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ase.domain.research_area import ResearchArea, area_from_dict, area_to_dict


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
