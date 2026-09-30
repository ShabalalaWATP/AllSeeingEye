"""Reviewed coverage for KAN-131 publisher feeds, not a reliability assessment."""

from ase.adapters.research.native_regions import NATIVE_COUNTRIES
from ase.application.research.source_allocation_types import AllocationProfile

NATIVE_REVIEW_DATE = "2026-09-30"

_TERMS = (
    "politics government",
    "diplomacy",
    "conflict war",
    "security",
    "economy trade",
    "humanitarian",
    "elections",
    "protests",
)


def native_allocation_profiles() -> dict[str, AllocationProfile]:
    """Explicit IDs prevent unreviewed future seeds entering the allocation inventory."""
    reviewed = (
        ("bbc_arabic", "Middle East Arabic"),
        ("bbc_hindi", "India South Asia Hindi"),
        ("bbc_urdu", "Pakistan South Asia Urdu"),
        ("bbc_japanese", "Japan Japanese"),
        ("bbc_korean", "Korea Korean"),
        ("bbc_hausa", "West Africa Hausa"),
        ("bbc_swahili", "East Africa Swahili"),
        ("bbc_afrique", "Africa French"),
        ("trt_haber_tr", "Turkey Türkiye Turkish"),
        ("ndtv_hindi", "India Hindi"),
        ("express_urdu", "Pakistan Urdu"),
        ("radio_okapi_fr", "DRC Congo French"),
        ("deutschlandfunk_de", "Germany German"),
        ("anadolu_ar", "Middle East Türkiye Arabic"),
        ("maariv_he", "Israel Hebrew"),
    )
    return {
        f"research_regional_{source_id}": AllocationProfile(
            (*_TERMS, focus),
            f"{NATIVE_REVIEW_DATE}: Publisher-advertised native headlines, F6 unassessed. "
            "Coverage is editorial focus, not incident geography; editions share their owner.",
            NATIVE_COUNTRIES[source_id],
            local_language=True,
        )
        for source_id, focus in reviewed
    }
