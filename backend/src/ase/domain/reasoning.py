"""Per-purpose reasoning effort, so mechanical work does not bill at report effort.

Reasoning tokens bill as output tokens on the profiles this app targets, so the effort
an operator chooses for a report is the single largest lever on the monthly bill.  The
work that never reaches a reader (title translation, conflict screening, claim
proposals, the economy explainer, the Ukraine digest and connection tests) does not
need it.  Analytical work (reports and their sections, direction, devil's advocacy,
Ask Eye, research planning, photo geolocation) keeps whatever the operator chose.

A purpose here is the request's ``schema_name``: every request builder already sets one
and it is the only purpose identifier that reaches the provider gateway.
"""

from __future__ import annotations

from dataclasses import dataclass

from ase.domain.llm import ReasoningEffort

# Work whose output is consumed by the app rather than read as analysis.
MECHANICAL_PURPOSES: frozenset[str] = frozenset(
    {
        "translation",
        "query_translation",
        "conflict_screening",
        "claim_proposals",
        "economy_explainer",
        "ukraine_digest",
        "connection_test",
    }
)
DEFAULT_MECHANICAL_EFFORT = ReasoningEffort.MEDIUM
# Accepted alongside the effort names to keep the operator's own choice everywhere.
INHERIT = "inherit"
# Cheapest first. Used only to compare two explicit choices, never to invent one.
EFFORT_ORDER: tuple[ReasoningEffort, ...] = (
    ReasoningEffort.NONE,
    ReasoningEffort.MINIMAL,
    ReasoningEffort.LOW,
    ReasoningEffort.MEDIUM,
    ReasoningEffort.HIGH,
    ReasoningEffort.XHIGH,
    ReasoningEffort.MAX,
)


def parse_mechanical_effort(value: str) -> ReasoningEffort | None:
    """``inherit`` (or a blank value) keeps the profile's effort for every purpose."""
    text = value.strip().lower()
    if not text or text == INHERIT:
        return None
    try:
        return ReasoningEffort(text)
    except ValueError:
        choices = ", ".join([INHERIT, *(item.value for item in ReasoningEffort)])
        raise ValueError(f"Choose a reasoning effort from: {choices}.") from None


def parse_mechanical_purposes(value: str) -> frozenset[str]:
    """A blank list keeps the built-in set; otherwise the operator's list replaces it."""
    names = {item.strip().lower() for item in value.split(",") if item.strip()}
    if not names:
        return MECHANICAL_PURPOSES
    if any(len(name) > 64 or not name.replace("_", "").isalnum() for name in names):
        raise ValueError("Mechanical purposes are comma separated schema names.")
    return frozenset(names)


@dataclass(frozen=True, slots=True)
class ReasoningEffortPolicy:
    """Which purposes are capped, and at what effort. Inactive when ``effort`` is None."""

    effort: ReasoningEffort | None = DEFAULT_MECHANICAL_EFFORT
    purposes: frozenset[str] = MECHANICAL_PURPOSES

    @property
    def active(self) -> bool:
        return self.effort is not None

    def applies_to(self, purpose: str) -> bool:
        return self.active and purpose.strip().lower() in self.purposes

    def effort_for(
        self, purpose: str, configured: ReasoningEffort | None
    ) -> ReasoningEffort | None:
        """The effort one call should use, given the profile's configured effort.

        This only ever lowers a choice.  A profile that already asks for less than the
        cap keeps its setting, and a profile with no explicit effort keeps the provider
        default rather than being pushed up to the cap.
        """
        if self.effort is None or configured is None or not self.applies_to(purpose):
            return configured
        return min(self.effort, configured, key=EFFORT_ORDER.index)
