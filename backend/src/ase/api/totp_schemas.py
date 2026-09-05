"""Only the enrolment response discloses a newly generated TOTP secret."""

from pydantic import BaseModel, Field


class TotpStatusOut(BaseModel):
    enabled: bool
    available: bool


class TotpEnrolIn(BaseModel):
    password: str = Field(min_length=1, max_length=128, repr=False)


class TotpConfirmIn(BaseModel):
    code: str = Field(pattern=r"^[0-9]{6}$", repr=False)


class TotpDisableIn(TotpEnrolIn):
    code: str = Field(pattern=r"^[0-9]{6}$", repr=False)


class TotpEnrolOut(BaseModel):
    secret: str = Field(repr=False)
    provisioning_uri: str = Field(repr=False)
    expires_in: int = 600
