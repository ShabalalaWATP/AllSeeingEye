"""Strict bounded public enquiry input, with no client-controlled status or recipients."""

from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from ase.domain.enterprise_enquiries import (
    DeploymentInterest,
    EnquiryDetails,
    EnquiryStatus,
    EnterpriseEnquiry,
    ExpectedUsers,
    clean_text,
)


class EnquiryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=254)
    organisation: str = Field(min_length=1, max_length=150)
    role: str = Field(default="", max_length=100)
    deployment_interest: DeploymentInterest
    expected_users: ExpectedUsers
    message: str = Field(default="", max_length=2000)
    website: str = Field(default="", max_length=200)

    @field_validator("name", "email", "organisation", "role", mode="before")
    @classmethod
    def single_line(cls, value: object) -> object:
        return clean_text(value, 254) if isinstance(value, str) else value

    @field_validator("message", mode="before")
    @classmethod
    def multiline(cls, value: object) -> object:
        return clean_text(value, 2000, multiline=True) if isinstance(value, str) else value

    def details(self) -> EnquiryDetails:
        return EnquiryDetails(
            self.name,
            str(self.email),
            self.organisation,
            self.deployment_interest,
            self.expected_users,
            self.role,
            self.message,
        )


class EnquiryStatusIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: EnquiryStatus


class EnquiryOut(BaseModel):
    id: UUID
    name: str
    email: str
    organisation: str
    role: str
    deployment_interest: DeploymentInterest
    expected_users: ExpectedUsers
    message: str
    status: EnquiryStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, item: EnterpriseEnquiry) -> "EnquiryOut":
        return cls(
            id=item.id,
            **asdict(item.details),
            status=item.status,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


class EnquiriesOut(BaseModel):
    items: list[EnquiryOut]
    total: int
