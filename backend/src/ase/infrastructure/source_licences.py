"""Validate packaged source rights before constructing any network-capable services."""

import json
from importlib.resources import files
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ase.domain.source_licences import CommercialUse, SourceLicence, SourceLicencePolicy

Rights = Literal["unknown", "conditional", "permission_required"]


class _Evidence(BaseModel):
    commercial_use_policy: CommercialUse
    commercial_use: Rights
    hosted_multi_user_use: Rights
    review_status: Literal[
        "terms_checked",
        "partial_review",
        "lookup_blocked",
        "lookup_inconclusive",
        "not_reviewed",
        "per_item_required",
    ]


class _EvidenceDocument(BaseModel):
    schema_version: Literal[1]
    policies: dict[str, _Evidence]


class _Source(BaseModel):
    model_config = ConfigDict(strict=True)
    id: str = Field(min_length=1, max_length=200, pattern=r"^[a-z0-9:_-]+$")
    family: str
    policy: str
    additional_policies: list[str]
    commercial_use: CommercialUse
    attribution_required: bool
    licence_ref: str


class _Register(BaseModel):
    schema_version: Literal[1]
    sources: list[_Source] = Field(min_length=1)


def parse_source_licences(register: object, evidence: object) -> tuple[SourceLicence, ...]:
    """Reject incomplete records and permissions widened beyond reviewed components."""
    sources = _Register.model_validate(register).sources
    policies = _EvidenceDocument.model_validate(evidence).policies
    seen: set[str] = set()
    result = []
    for row in sources:
        if row.id in seen:
            raise ValueError(f"Duplicate source licence metadata: {row.id}")
        seen.add(row.id)
        if row.licence_ref != f"docs/SOURCE_LICENCES.md#source-{row.id}":
            raise ValueError(f"Invalid source licence reference: {row.id}")
        keys = [row.policy, *row.additional_policies]
        if len(keys) != len(set(keys)):
            raise ValueError(f"Repeated source policy: {row.id}")
        if any(key not in policies for key in keys):
            raise ValueError(f"Missing policy for source: {row.id}")
        if row.commercial_use != "forbidden" and any(
            policies[key].commercial_use_policy == "forbidden" for key in keys
        ):
            raise ValueError(f"Source includes a forbidden commercial component: {row.id}")
        if row.commercial_use == "allowed" and (
            row.family == "camera_index"
            or any(
                policies[key].review_status != "terms_checked"
                or policies[key].commercial_use_policy != "allowed"
                or policies[key].commercial_use != "conditional"
                or policies[key].hosted_multi_user_use != "conditional"
                for key in keys
            )
        ):
            raise ValueError(f"Source is not fully reviewed for commercial use: {row.id}")
        result.append(
            SourceLicence(row.id, row.commercial_use, row.attribution_required, row.licence_ref)
        )
    return tuple(result)


def load_source_licences(
    *, commercial_use: bool = False, acknowledgements: frozenset[str] = frozenset()
) -> SourceLicencePolicy:
    resources = files("ase.resources")
    entries = parse_source_licences(
        json.loads(resources.joinpath("source_licences.json").read_text(encoding="utf-8")),
        json.loads(resources.joinpath("source_licence_policies.json").read_text(encoding="utf-8")),
    )
    if unknown := acknowledgements - {entry.source_id for entry in entries}:
        raise ValueError(f"Unknown source licence acknowledgement: {', '.join(sorted(unknown))}")
    return SourceLicencePolicy(
        entries, commercial_use=commercial_use, acknowledgements=acknowledgements
    )
