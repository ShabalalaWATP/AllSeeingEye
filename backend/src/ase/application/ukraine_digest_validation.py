"""Mechanical checks a generated digest must pass before anything is stored.

These are arithmetic and string checks, not judgement. They cannot tell whether the model
understood the fortnight, only that it cited evidence that exists, copied numbers and dates
from the pack, invented no links and stayed inside its bounds.
"""

from __future__ import annotations

import re
from datetime import date

from ase.application.ukraine_digest_evidence import EvidencePack
from ase.domain.ukraine.digest import MAX_PAYLOAD_BYTES, UkraineDigest

_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_LINK = re.compile(r"https?://|www\.", re.IGNORECASE)
MAX_ERRORS = 10


def _canonical(token: str) -> str:
    """1,234 and 01234 both read as 1234 so wording cannot defeat the comparison."""
    cleaned = token.replace(",", "")
    if "." in cleaned:
        whole, _, fraction = cleaned.partition(".")
        return f"{whole.lstrip('0') or '0'}.{fraction.rstrip('0') or '0'}"
    return cleaned.lstrip("0") or "0"


def _numbers(text: str) -> set[str]:
    return {_canonical(match.group()) for match in _NUMBER.finditer(text)}


def _check_period(digest: UkraineDigest, pack: EvidencePack) -> list[str]:
    if (digest.period.starts_on, digest.period.ends_on) == (pack.period_start, pack.period_end):
        return []
    return [
        "The period must be restated exactly as "
        f"{pack.period_start.isoformat()} to {pack.period_end.isoformat()}."
    ]


def _check_citations(digest: UkraineDigest, known: set[str]) -> list[str]:
    errors: list[str] = []
    for change in digest.changes():
        missing = sorted(set(change.source_ids) - known)
        if missing:
            errors.append(
                f"These evidence ids are not in the pack: {', '.join(missing)}. "
                f"Cite only ids that exist. Change: {change.text[:80]}"
            )
        if len(set(change.source_ids)) != len(change.source_ids):
            errors.append(f"An evidence id is repeated in one change: {change.text[:80]}")
    return errors


def _check_numbers(texts: tuple[str, ...], allowed: set[str]) -> list[str]:
    errors: list[str] = []
    for text in texts:
        unknown = sorted(_numbers(text) - allowed)
        if unknown:
            errors.append(
                f"These numbers do not appear in the pack: {', '.join(unknown)}. "
                f"Use only figures copied from the pack. Text: {text[:80]}"
            )
    return errors


def _check_dates(texts: tuple[str, ...], start: date, end: date) -> list[str]:
    errors: list[str] = []
    for text in texts:
        for match in _ISO_DATE.finditer(text):
            try:
                value = date.fromisoformat(match.group())
            except ValueError:
                errors.append(f"{match.group()} is not a real date. Text: {text[:80]}")
                continue
            if not start <= value <= end:
                errors.append(
                    f"{match.group()} falls outside the period "
                    f"{start.isoformat()} to {end.isoformat()}. Text: {text[:80]}"
                )
    return errors


def _check_style(texts: tuple[str, ...]) -> list[str]:
    errors: list[str] = []
    for text in texts:
        if _LINK.search(text):
            errors.append(f"Do not write links; cite evidence ids instead. Text: {text[:80]}")
        if "—" in text:
            errors.append(f"Do not use em dashes. Text: {text[:80]}")
    return errors


def validate_digest(digest: UkraineDigest, pack: EvidencePack) -> tuple[str, ...]:
    """Every failed check, in a form that can be handed straight back to the model."""
    texts = digest.texts()
    # The pack JSON carries every evidence id, date, label and detail the model may copy.
    allowed = _numbers(pack.as_json()) | {
        _canonical(str((pack.period_end - pack.period_start).days)),
        _canonical(str(len(pack.items))),
    }
    errors = [
        *_check_period(digest, pack),
        *_check_citations(digest, {item.id for item in pack.items}),
        *_check_numbers(texts, allowed),
        *_check_dates(texts, pack.period_start, pack.period_end),
        *_check_style(texts),
    ]
    if len(digest.model_dump_json().encode()) > MAX_PAYLOAD_BYTES:
        errors.append("The digest is too long. Shorten the summaries and changes.")
    return tuple(errors[:MAX_ERRORS])
