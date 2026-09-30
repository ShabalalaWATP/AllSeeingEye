"""One shared disposition per alert; counts use UTC acknowledgement days."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class AlertDisposition(StrEnum):
    USEFUL = "useful"
    NOISE = "noise"
    DUPLICATE = "duplicate"


@dataclass(frozen=True, slots=True)
class AlertFeedback:
    indicator_id: UUID
    since: datetime
    until: datetime
    useful: int = 0
    noise: int = 0
    duplicate: int = 0
    time_basis: str = "UTC acknowledgement day; today and the previous 29 days"
