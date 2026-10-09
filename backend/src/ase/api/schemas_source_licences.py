"""Reviewed deployment policy, without credentials or private permission correspondence."""

from pydantic import BaseModel, ConfigDict

from ase.domain.source_licences import CommercialUse


class SourceLicenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    commercial_use: CommercialUse
    attribution_required: bool
    licence_ref: str
    available: bool
    acknowledged: bool
    reason: str
