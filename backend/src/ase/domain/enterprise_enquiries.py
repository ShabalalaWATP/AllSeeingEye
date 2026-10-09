"""Validated operator enquiries, separate from account provisioning."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from unicodedata import category
from uuid import UUID

from email_validator import validate_email


class DeploymentInterest(StrEnum):
    OWN_CLOUD = "own_cloud"
    ON_PREMISES = "on_premises"
    AIR_GAPPED = "air_gapped"
    UNDECIDED = "undecided"


class ExpectedUsers(StrEnum):
    SMALL = "1_10"
    MEDIUM = "11_50"
    LARGE = "51_250"
    ENTERPRISE = "250_plus"


class EnquiryStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    CLOSED = "closed"


def clean_text(value: str, maximum: int, *, multiline: bool = False, required: bool = False) -> str:
    if not multiline and ("\r" in value or "\n" in value):
        raise ValueError("Single-line fields cannot contain line breaks")
    value = "".join(
        char for char in value if category(char) not in {"Cc", "Cf"} or (multiline and char == "\n")
    ).strip()
    if len(value) > maximum or (required and not value):
        raise ValueError(f"Use {'1' if required else '0'} to {maximum} characters")
    return value


@dataclass(frozen=True, slots=True)
class EnquiryDetails:
    name: str
    email: str
    organisation: str
    deployment_interest: DeploymentInterest
    expected_users: ExpectedUsers
    role: str = ""
    message: str = ""

    def __post_init__(self) -> None:
        for field, maximum, required in (
            ("name", 100, True),
            ("organisation", 150, True),
            ("role", 100, False),
        ):
            object.__setattr__(
                self, field, clean_text(getattr(self, field), maximum, required=required)
            )
        email = clean_text(self.email, 254, required=True)
        email = validate_email(email, check_deliverability=False).normalized.lower()
        if len(email) > 254:
            raise ValueError("Email must be at most 254 characters")
        object.__setattr__(self, "email", email)
        object.__setattr__(self, "message", clean_text(self.message, 2000, multiline=True))
        object.__setattr__(
            self, "deployment_interest", DeploymentInterest(self.deployment_interest)
        )
        object.__setattr__(self, "expected_users", ExpectedUsers(self.expected_users))


@dataclass(frozen=True, slots=True)
class EnterpriseEnquiry:
    id: UUID
    details: EnquiryDetails
    status: EnquiryStatus
    created_at: datetime
    updated_at: datetime
