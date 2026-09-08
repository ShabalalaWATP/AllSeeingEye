"""Read historical two-field variants and omit absent provenance on round trips."""

from collections.abc import Mapping
from dataclasses import asdict
from typing import Any

from ase.domain.research_plan import QueryVariant


def variant_from_dict(row: Mapping[str, Any] | None) -> QueryVariant | None:
    if row is None:
        return None
    return QueryVariant(
        **{
            **row,
            "terms": tuple(row["terms"]),
            "original_terms": tuple(row.get("original_terms", ())),
        }
    )


def required_variant(row: Mapping[str, Any]) -> QueryVariant:
    value = variant_from_dict(row)
    if value is None:
        raise ValueError("A query variant is required")
    return value


def omit_variant_defaults(row: dict[str, Any]) -> None:
    for key, default in (
        ("kind", "translation"),
        ("original_terms", ()),
        ("source_script", None),
        ("target_script", None),
        ("method", None),
    ):
        if row.get(key) == default:
            row.pop(key, None)


def variant_to_dict(value: QueryVariant) -> dict[str, Any]:
    result = asdict(value)
    omit_variant_defaults(result)
    return result


def validate_variant_anchors(
    variants: tuple[QueryVariant, ...], terms: tuple[str, ...] | None
) -> None:
    for variant in variants:
        if variant.original_terms and variant.original_terms != terms:
            raise ValueError("Transliteration must reference the exact original query terms")


def describe_variant(value: QueryVariant | None) -> str:
    if value is None:
        return ""
    return (
        f" Query {value.kind}, language {value.language}; "
        f"original terms {value.original_terms or 'not recorded'}; "
        f"executed terms {value.terms}; scripts {value.source_script or 'unknown'} to "
        f"{value.target_script or 'unknown'}; method {value.method or 'not recorded'}. "
        "Query variants are unverified search input."
    )
