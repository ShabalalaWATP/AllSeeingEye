"""A drawn area or map object gets the area product, and the old restrictions hold."""

from __future__ import annotations

from uuid import uuid4

import pytest

from ase.api.schemas_reports import ReportCreateIn
from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import AREA_TEMPLATES, TEMPLATES, template_for
from ase.domain.research import ResearchMode
from ase.domain.research_area import ResearchArea
from test_map_research_origin import AREA

QUESTION = "What is happening inside this area?"


def _area_input() -> dict[str, object]:
    return {"geometry": AREA.to_collection()}


def _area() -> ResearchArea:
    return ResearchArea(AREA)


def _payload(**overrides: object) -> dict[str, object]:
    return {
        "template": "ask",
        "question": QUESTION,
        "research_mode": "detailed",
        "research_area": _area_input(),
        "disclose_area_to_provider": True,
        **overrides,
    }


def test_the_area_product_asks_for_what_a_drawn_area_needs() -> None:
    sections = " ".join(TEMPLATES["area_brief"].sections).lower()
    assert "reporting by theme within the area" in sections
    assert "concentrated" in sections and "changed inside the area" in sections
    assert "indicators and warning for this area" in sections
    assert "collection recommendations" in sections
    assert "a drawn area is a collection choice" in sections
    assert "publisher's remit is not geography" in sections
    assert TEMPLATES["area_brief"].needs_question
    assert TEMPLATES["area_brief"].strategy == TEMPLATES["ask"].strategy


def test_the_area_product_keeps_what_ask_does_well() -> None:
    sections = " ".join(TEMPLATES["area_brief"].sections).lower()
    assert "the answer to the question asked of this area" in sections
    assert "alternative hypotheses" in sections
    assert "sourcing statement" in sections


def test_a_new_drawn_area_request_is_promoted_to_the_area_product() -> None:
    assert ReportCreateIn(**_payload()).to_request().template_id == "area_brief"


def test_a_saved_map_object_request_is_promoted_too() -> None:
    view, revision = uuid4(), uuid4()
    payload = _payload(research_area=None, map_view_id=str(view), map_revision_id=str(revision))
    assert ReportCreateIn(**payload).to_request().template_id == "area_brief"


def test_an_explicit_choice_is_never_overridden() -> None:
    assert ReportCreateIn(**_payload(template="area_brief")).to_request().template_id == (
        "area_brief"
    )


def test_an_ordinary_request_is_untouched() -> None:
    payload = {"template": "ask", "question": "What changed?", "research_mode": "quick"}
    assert ReportCreateIn(**payload).to_request().template_id == "ask"


def test_an_existing_saved_area_report_still_rebuilds_from_its_stored_template() -> None:
    scope = {
        "question": QUESTION,
        "research_mode": "detailed",
        "research_area": {"geometry": AREA.to_collection(), "sha256": AREA.sha256},
    }
    rebuilt = ReportRequest.from_scope("ask", scope)
    assert rebuilt.template_id == "ask"
    assert rebuilt.effective_area is not None


@pytest.mark.parametrize("template_id", sorted(AREA_TEMPLATES))
def test_both_area_products_accept_a_drawn_area(template_id: str) -> None:
    assert template_for(template_id).needs_question
    request = ReportRequest(
        template_id,
        question=QUESTION,
        research_mode=ResearchMode.DETAILED,
        research_area=_area(),
    )
    assert request.effective_area is not None


@pytest.mark.parametrize(
    "extra",
    [
        {"plan_id": uuid4()},
        {"country_iso": "UA"},
        {"conflict_id": "ukraine"},
        {"hazard": "flood"},
        {"map_view_id": uuid4(), "map_revision_id": uuid4()},
    ],
)
def test_a_drawn_area_still_cannot_be_combined_with_another_scope(
    extra: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        ReportRequest(
            "area_brief",
            question=QUESTION,
            research_mode=ResearchMode.DETAILED,
            research_area=_area(),
            **extra,
        )


def test_an_unrelated_product_still_cannot_take_a_drawn_area() -> None:
    with pytest.raises(ValueError):
        ReportRequest(
            "intsum",
            question=QUESTION,
            research_mode=ResearchMode.DETAILED,
            research_area=_area(),
        )
