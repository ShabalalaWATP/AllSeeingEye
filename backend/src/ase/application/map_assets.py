"""Policy projection leaves the raw packaged catalogue available to inventory metadata."""

from collections.abc import Mapping
from typing import Any

from ase.domain.map_licences import INFRASTRUCTURE_SOURCES
from ase.domain.source_licences import SourceLicencePolicy


def available_infrastructure(
    snapshot: Mapping[str, Any], licences: SourceLicencePolicy
) -> dict[str, Any]:
    result = dict(snapshot)
    for field, source_id in INFRASTRUCTURE_SOURCES.items():
        if not licences.allowed(source_id):
            result[field] = []
    return result
