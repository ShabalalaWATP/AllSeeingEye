"""Reviewed allocation hints for explicit E03 structured research bridges."""

from ase.application.research.source_allocation_types import AllocationProfile


def e03_allocation_profiles(review_date: str) -> dict[str, AllocationProfile]:
    return {
        "research-ioda-outage-events": AllocationProfile(
            ("internet", "connectivity", "outage", "network", "IODA", "measurement"),
            f"{review_date}: IODA country anomaly windows, not an attributed cyberattack "
            "or proof of service impact; first 20 only and operator permission required.",
            (),
            True,
            False,
        ),
        "research-ecb-gbp-reference-rate": AllocationProfile(
            ("ECB", "GBP", "EUR", "exchange", "currency", "rate", "sterling"),
            f"{review_date}: ECB daily GBP-per-EUR reference rates, not transaction prices "
            "or a broad economic series; exact subject and recorded dates required.",
            ("GB",),
            True,
            False,
        ),
    }
