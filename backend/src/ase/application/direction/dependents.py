"""Refuse deleting a direction object that other records still use.

Clearing the link instead would silently widen what a plan watches or what an alert rule's
report covers. Widening a restriction needs an explicit choice, so the caller changes or
deletes the dependent records first.
"""

from __future__ import annotations

from ase.domain.collection import LinkedRecords
from ase.domain.errors import Conflict

NAMES_SHOWN = 5


def linked_names(links: LinkedRecords) -> str:
    shown = links.visible_names[:NAMES_SHOWN]
    hidden = links.total - len(shown)
    names = ", ".join(shown)
    if not shown:
        return f"{hidden} that you cannot open"
    return f"{names} and {hidden} more" if hidden > 0 else names


def refuse_if_linked(
    links: LinkedRecords, *, subject: str, singular: str, plural: str, remedy: str
) -> None:
    """Raise a conflict that names the dependent records the caller can read."""
    if links.total <= 0:
        return
    noun = singular if links.total == 1 else plural
    raise Conflict(
        f"This {subject} is used by {links.total} {noun}: {linked_names(links)}. "
        f"{remedy}, then delete this {subject}."
    )


def refuse_area_in_use(links: LinkedRecords) -> None:
    refuse_if_linked(
        links,
        subject="area",
        singular="collection plan",
        plural="collection plans",
        remedy="Choose another area for those plans or delete them",
    )


def refuse_plan_in_use(links: LinkedRecords) -> None:
    refuse_if_linked(
        links,
        subject="plan",
        singular="alert rule",
        plural="alert rules",
        remedy="Remove the plan from those alert rules or delete them",
    )
