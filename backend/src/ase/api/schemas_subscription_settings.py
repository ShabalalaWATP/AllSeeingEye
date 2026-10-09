"""A closed request surface for editing brief-linked subscription settings."""

from pydantic import BaseModel, ConfigDict, Field

from ase.application.schedules.edit_brief_settings import BriefSettingsInput
from ase.domain.errors import InvalidRequest
from ase.domain.subscription_recurrence import LocalRecurrence


class BriefSubscriptionSettingsIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    expected_revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    name: str = Field(min_length=1, max_length=120)
    timezone: str = Field(min_length=1, max_length=100)
    local_hour: int = Field(ge=0, le=23)
    local_minute: int = Field(ge=0, le=59)
    cadence: str = Field(min_length=1, max_length=16)
    weekday: int = Field(ge=0, le=6)
    monthday: int = Field(ge=1, le=31)
    anchor_month: int = Field(ge=1, le=12)

    def to_input(self) -> BriefSettingsInput:
        try:
            recurrence = LocalRecurrence(
                self.timezone,
                self.local_hour,
                self.local_minute,
                self.cadence,
                self.weekday,
                self.monthday,
                self.anchor_month,
            )
        except ValueError as exc:
            field = "timezone" if "timezone" in str(exc) else "cadence"
            raise InvalidRequest(str(exc), fields={field: str(exc)}) from exc
        return BriefSettingsInput(self.expected_revision, self.name, recurrence)
