"""Bounded public dashboard DTOs; timestamps distinguish retrieval from observation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ase.domain.economy import SeriesFrequency, SeriesStatus


class EconomyPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, allow_inf_nan=False)
    date: str
    value: float | None


class EconomySeriesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    unit: str
    frequency: SeriesFrequency
    provider: str
    source_url: str
    status: SeriesStatus
    note: str
    updated_at: datetime | None = Field(description="Last successful retrieval of this series.")
    source_updated_at: str | None = Field(description="Provider publication date when supplied.")
    points: list[EconomyPointOut] = Field(max_length=90)


class EconomyRegionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    series: list[EconomySeriesOut] = Field(max_length=4)


class EconomySnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    fetched_at: datetime
    refresh_after: datetime
    regions: list[EconomyRegionOut] = Field(max_length=6)
    fx: list[EconomySeriesOut] = Field(max_length=5)
