"""Explicit provider military classifications, never identity-string guesses."""

from ase.domain.events import Category, Event


def is_reported_military(event: Event) -> bool:
    if event.category not in {Category.AVIATION, Category.MARITIME}:
        return False
    if "military" in event.tags or event.attributes.get("military") is True:
        return True
    if event.category is Category.AVIATION:
        return event.subtype == "military_aircraft"
    return event.attributes.get("ship_type_code") == 35
