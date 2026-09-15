"""The fact pack is the only ground truth the explainer, and its checks, ever see."""

from __future__ import annotations

import json
from datetime import timedelta

from ase.application.economy_explainer_facts import build_fact_pack, fact_document, fingerprint
from ase.application.economy_explainer_prompt import explainer_request, explainer_schema
from ase.domain.economy_explainer import REGION_IDS
from economy_explainer_helpers import NOW, explainer_profile, headline, snapshot


def pack(growth: float = 2.4, fetched_at=NOW):
    return build_fact_pack(snapshot(growth, fetched_at), (headline(),))


def test_percentage_units_report_a_percentage_point_change_and_shares_report_a_percentage():
    facts = pack().region("GB")
    assert facts is not None
    growth = next(item for item in facts.indicators if item.id == "growth")
    assert (growth.latest_year, growth.latest_value) == ("2024", 2.4)
    assert (growth.previous_year, growth.previous_value) == ("2023", 1.2)
    assert (growth.change, growth.change_kind) == (1.2, "percentage_point")


def test_gaps_series_status_and_missing_observations_are_stated_not_bridged():
    facts = pack().region("US")
    assert facts is not None
    inflation = next(item for item in facts.indicators if item.id == "inflation")
    # 2023 has no observation; the previous observation is 2022, never an invented 2023.
    assert inflation.previous_year == "2022"
    assert inflation.missing_years == ("2023",)
    unemployment = next(item for item in facts.indicators if item.id == "unemployment")
    assert (unemployment.status, unemployment.latest_value) == ("unavailable", None)
    assert (facts.available, facts.unavailable) == (2, 1)


def test_headlines_carry_publisher_and_date_for_their_region_only():
    facts = pack()
    gb = facts.region("GB")
    russia = facts.region("RU")
    assert gb is not None and russia is not None
    assert [(item.publisher, item.published_on) for item in gb.headlines] == [
        ("Reuters Business", "2026-08-31")
    ]
    assert russia.headlines == ()
    # A worldwide summary still sees the dated headline pool.
    world = facts.region("WORLD")
    assert world is not None and len(world.headlines) == 1


def test_fact_document_never_carries_a_link_or_the_retrieval_time():
    document = json.dumps(fact_document(pack()))
    assert "http" not in document
    assert NOW.isoformat() not in document


def test_fingerprint_ignores_a_refetch_but_moves_when_a_figure_moves():
    unchanged = fingerprint(pack(fetched_at=NOW + timedelta(hours=6)))
    assert fingerprint(pack()) == unchanged
    assert fingerprint(pack(growth=2.5)) != unchanged


def test_exchange_rates_keep_their_observation_dates():
    [rate] = pack().fx
    assert (rate.observed_on, rate.value) == ("2026-09-01", 0.86)
    assert (rate.previous_on, rate.previous_value) == ("2026-08-31", 0.85)


def test_schema_requires_every_supplied_region_and_bounds_each_field():
    schema = explainer_schema([region.id for region in pack().regions])
    assert schema["properties"]["regions"]["required"] == list(REGION_IDS[1:])
    world = schema["properties"]["world"]["properties"]
    assert world["paragraphs"]["minItems"] == 2
    assert world["takeaway"]["maxLength"] == 200


async def test_the_prompt_states_the_house_rules_and_carries_only_supplied_facts(container):
    profile = await explainer_profile(container)
    request = explainer_request(profile, pack())
    system, user = request.messages
    assert "British English" in system.content and "em dash" in system.content
    assert "never as predictions" in user.content or "never as a prediction" in user.content
    assert "Reuters Business" in user.content and '"2.4"' not in user.content
    assert "2.4" in user.content and "http" not in user.content
    assert request.schema_name == "economy_explainer"
    assert request.max_output_tokens == 6000


async def test_a_retry_repeats_the_rejection_reasons_to_the_model(container):
    profile = await explainer_profile(container)
    request = explainer_request(profile, pack(), ["the figure 9.9 does not match any supplied"])
    assert "9.9 does not match any supplied" in request.messages[1].content
    assert "rejected by an automatic check" in request.messages[1].content
