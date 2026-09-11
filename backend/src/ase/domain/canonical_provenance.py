"""Dataclass snapshots retaining pre-provenance canonical bytes for absent additions.

New defaults and redundant singleton scopes are omitted by record type. Arbitrary
user dictionary keys and pre-existing optional fields retain their historical shape.
"""

from dataclasses import fields, is_dataclass
from typing import Any

from ase.domain.evidence import EvidenceItem
from ase.domain.research import CollectionAttempt
from ase.domain.research_plan import QueryVariant, ResearchPlan, ResearchTask
from ase.domain.research_records import ResearchReceipt


def canonical_snapshot(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        result = {
            field.name: canonical_snapshot(getattr(value, field.name)) for field in fields(value)
        }
        defaults: tuple[tuple[str, Any], ...] = ()
        if isinstance(value, EvidenceItem):
            defaults = (("transformations", ()), ("source_dates", ()))
        elif isinstance(value, QueryVariant):
            defaults = (
                ("kind", "translation"),
                ("original_terms", ()),
                ("source_script", None),
                ("target_script", None),
                ("method", None),
            )
        elif isinstance(value, ResearchTask | CollectionAttempt):
            defaults = (("query_variant", None),)
        elif isinstance(value, ResearchReceipt):
            defaults = (("web_research", None),)
        elif isinstance(value, ResearchPlan):
            defaults = (("country_isos", ()), ("research_web_search", False))
        for key, default in defaults:
            if result[key] == default:
                del result[key]
        if (
            isinstance(value, ResearchPlan)
            and value.country_iso
            and value.country_isos == (value.country_iso,)
        ):
            # The legacy singular field still binds this exact country. Keep
            # genuinely plural choices, whose meaning it cannot represent.
            result.pop("country_isos", None)
        return result
    if isinstance(value, dict):
        return {key: canonical_snapshot(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(canonical_snapshot(item) for item in value)
    if isinstance(value, list):
        return [canonical_snapshot(item) for item in value]
    return value
