"""Explicit registry namespaces and original operator input, never name resolution."""

import re
from dataclasses import dataclass
from typing import Any, Literal

RegistryNamespace = Literal["lei", "sec_cik", "gb_company_number"]


def registry_subject(namespace: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 300:
        raise ValueError("Provide a bounded explicit registry identifier")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("Invalid registry identifier characters")
    original = value.strip().upper()
    if namespace == "lei":
        number = original.removeprefix("LEI:").strip()
        if re.fullmatch(r"[A-Z0-9]{18}[0-9]{2}", number):
            return "LEI:" + number
    elif namespace == "sec_cik":
        match = re.fullmatch(r"(?:CIK\s*:?\s*)?([0-9]{1,10})", original)
        if match and int(match[1]):
            return "CIK:" + match[1].zfill(10)
    elif namespace == "gb_company_number":
        number = original
        for prefix in ("COMPANIES-HOUSE:", "GB:"):
            if number.startswith(prefix):
                number = number[len(prefix) :].strip()
                break
        if re.fullmatch(r"[0-9]{1,8}", number):
            return "GB:" + number.zfill(8)
        if re.fullmatch(r"(?:[A-Z]{2}[0-9]{6}|R[0-9]{7}|[A-Z]{2}[0-9]{5}[A-Z])", number):
            return "GB:" + number
    raise ValueError("Identifier does not match its explicit registry namespace")


@dataclass(frozen=True, slots=True)
class RegistryIdentifier:
    id: str
    namespace: RegistryNamespace
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", self.id):
            raise ValueError("Invalid registry identifier reference")
        registry_subject(self.namespace, self.value)


@dataclass(frozen=True, slots=True)
class RegistryLookup:
    candidate_id: str
    identifier_id: str
    namespace: RegistryNamespace
    original_value: str
    subject: str

    def __post_init__(self) -> None:
        RegistryIdentifier(self.identifier_id, self.namespace, self.original_value)
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", self.candidate_id):
            raise ValueError("Invalid lookup candidate reference")
        if registry_subject(self.namespace, self.original_value) != self.subject:
            raise ValueError("Registry lookup canonical subject mismatch")


def lookup_from_dict(value: Any) -> RegistryLookup | None:
    return RegistryLookup(**value) if value is not None else None


def describe_lookup(value: RegistryLookup | None) -> str:
    if value is None:
        return ""
    return (
        f" Exact {value.namespace} lookup for candidate {value.candidate_id}, identifier "
        f"{value.identifier_id}: original {value.original_value}; "
        f"effective subject {value.subject}. "
        "Operator-supplied identifier; disambiguation only, "
        "not a verified identity match or contrary search."
    )


def validate_lookup_anchor(
    value: RegistryLookup | None, purpose: str, candidate_id: str | None
) -> None:
    if value is not None and (
        not isinstance(value, RegistryLookup)
        or purpose != "disambiguation"
        or candidate_id != value.candidate_id
    ):
        raise ValueError("Registry lookup requires its exact disambiguation candidate anchor")
