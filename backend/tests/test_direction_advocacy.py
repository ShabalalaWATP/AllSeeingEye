"""The direction call for asks and the devil's advocacy pass: domain rules and the pipeline."""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient

from ase.application.ports.feeds import EventQuery
from ase.container import Container
from ase.domain.advocacy import (
    AdvocacyParseError,
    advocacy_from_dict,
    advocacy_to_dict,
    check_advocacy,
    lowered,
    parse_advocacy,
)
from ase.domain.direction import (
    DirectionParseError,
    direction_from_dict,
    direction_to_dict,
    parse_direction,
)
from ase.domain.doctrine import Confidence
from ase.domain.events import Category
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE, ScriptedGateway, filled_store, good_body

FULL_PROFILE = {**PROFILE, "roles": ["direction", "assessment", "devil"]}
DIRECTION = {
    "pir": "Will fighting around Kharkiv intensify this week?",
    "sirs": ["Force posture", "Strike tempo", "Strike tempo"],
    "eeis": ["Are reinforcements moving north?", "Has the strike rate risen?"],
    "search_terms": ["Kharkiv", "drone", ""],
    "categories": ["conflict", "nonsense"],
}
ADVOCACY = {
    "argument": "The strikes fit routine harassment rather than preparation.",
    "evidence": ["E2", "E7"],
    "lower_confidence": True,
    "rationale": "Two items from one theatre.",
}


def test_direction_parsing_bounds_and_round_trips() -> None:
    direction = parse_direction(DIRECTION)
    assert direction.sirs == ("Force posture", "Strike tempo")
    assert direction.search_terms == ("Kharkiv", "drone")
    assert direction.categories == (Category.CONFLICT,)
    assert direction.requirement_ids() == ("PIR-1", "SIR-1", "SIR-2", "EEI-1", "EEI-2")
    assert direction.lines()[0] == "PIR-1: Will fighting around Kharkiv intensify this week?"
    assert direction_from_dict(direction_to_dict(direction)) == direction
    assert parse_direction({"pir": "x", "sirs": [f"s{i}" for i in range(9)]}).sirs == tuple(
        f"s{i}" for i in range(6)
    )
    with pytest.raises(DirectionParseError):
        parse_direction([])
    with pytest.raises(DirectionParseError):
        parse_direction({"pir": "  "})
    with pytest.raises(DirectionParseError):
        parse_direction({"pir": "x", "eeis": "not a list"})
    with pytest.raises(DirectionParseError):
        parse_direction({"pir": "x", "eeis": [1]})


def test_advocacy_parsing_checks_and_confidence_steps() -> None:
    advocacy = parse_advocacy(ADVOCACY, "KJ1")
    checked, findings = check_advocacy(advocacy, frozenset({"E1", "E2"}))
    assert checked is not None and checked.evidence == ("E2",)
    assert [f.message for f in findings] == ["Unknown evidence E7 removed"]
    leaky = parse_advocacy({**ADVOCACY, "argument": "See https://evil.example/x"}, "KJ1")
    assert check_advocacy(leaky, frozenset({"E2"}))[0] is None
    assert lowered(Confidence.HIGH) is Confidence.MODERATE
    assert lowered(Confidence.MODERATE) is Confidence.LOW
    assert lowered(Confidence.LOW) is Confidence.LOW
    stored = advocacy_to_dict(checked)
    assert stored["confidence_before"] is None
    assert advocacy_from_dict({**stored, "confidence_before": "moderate"}).confidence_before is (
        Confidence.MODERATE
    )
    with pytest.raises(AdvocacyParseError):
        parse_advocacy("no", "KJ1")
    with pytest.raises(AdvocacyParseError):
        parse_advocacy({**ADVOCACY, "argument": ""}, "KJ1")
    with pytest.raises(AdvocacyParseError):
        parse_advocacy({**ADVOCACY, "evidence": "E1"}, "KJ1")


async def test_ask_runs_direction_then_the_advocate(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await seed_legacy_profile(container, FULL_PROFILE)
    container.store.upsert(list(filled_store().query(EventQuery(limit=10))))
    gateway = ScriptedGateway(json.dumps(DIRECTION), json.dumps(good_body()), json.dumps(ADVOCACY))
    container.llm = gateway
    response = await client.post(
        "/api/reports",
        json={
            "template": "ask",
            "question": "Will Kharkiv see more fighting?",
            "devils_advocacy": True,
        },
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    assert [r.schema_name for r in gateway.requests] == [
        "direction",
        "report",
        "advocacy",
        "claim_proposals",
    ]
    assert (
        "PIR-1: Will fighting around Kharkiv intensify this week?"
        in gateway.requests[1].messages[1].content
    )
    assert "Judgement KJ1:" in gateway.requests[2].messages[1].content
    version = response.json()["version"]
    assert version["direction"]["search_terms"] == ["Kharkiv", "drone"]
    assert version["direction"]["categories"] == ["conflict"]
    assert [item["title"] for item in version["evidence"]] == [
        "Drone strike near Sumy",
        "Shelling in Kharkiv",
        "Talks resume in Vienna",
    ]
    assert version["status"] == "ready"
    assert version["body"]["key_judgements"][0]["confidence"] == "low"
    advocacy = version["devils_advocacy"]
    assert advocacy["target"] == "KJ1" and advocacy["evidence"] == ["E2"]
    assert (advocacy["confidence_before"], advocacy["confidence_after"]) == ("moderate", "low")
    assert any("E7" in f["message"] for f in version["findings"])
    assert version["prompt_tokens"] == 200 and version["latency_ms"] == 400.0
    markdown = version["markdown"]
    assert "Requirements: PIR-1, SIR-1, SIR-2, EEI-1, EEI-2." in markdown
    assert "## Direction" in markdown and "## Devil's advocacy" in markdown
    assert "Confidence on KJ1 lowered from moderate to low." in markdown
    assert response.json()["report"]["scope"]["devils_advocacy"] is True

    # Regeneration keeps the scope: direction again, and an advocate who leaves confidence alone.
    unchanged = good_body(
        key_judgements=[
            {**judgement, "change_from_previous": "unchanged"}
            for judgement in good_body()["key_judgements"]
        ]
    )
    container.llm = ScriptedGateway(
        json.dumps(DIRECTION),
        json.dumps(unchanged),
        json.dumps({**ADVOCACY, "lower_confidence": False}),
    )
    again = await client.post(
        f"/api/reports/{response.json()['report']['id']}/versions", headers=bearer(token)
    )
    assert again.status_code == 201, again.text
    second = again.json()["version"]
    assert second["number"] == 2 and second["direction"]["pir"] == DIRECTION["pir"]
    assert second["body"]["key_judgements"][0]["confidence"] == "moderate"
    assert second["devils_advocacy"]["confidence_before"] is None
    assert "Confidence unchanged. Two items from one theatre." in second["markdown"]

    async with container.session_factory() as session:
        usage = await container.repositories(session).llm_usage.list_recent(10)
    assert sorted({row.purpose for row in usage}) == [
        "claim_proposals",
        "report:ask",
        "report:ask:advocacy",
        "report:ask:direction",
    ]


async def test_direction_and_advocacy_degrade_without_stopping_the_report(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    container.store.upsert(list(filled_store().query(EventQuery(limit=10))))
    ask = {"template": "ask", "question": "What next?", "devils_advocacy": True}

    # No profile plays the direction or devil roles: warnings, and the report still lands.
    await seed_legacy_profile(container, PROFILE)
    container.llm = ScriptedGateway(json.dumps(good_body()))
    plain = await client.post("/api/reports", json=ask, headers=bearer(token))
    assert plain.status_code == 201
    messages = [f["message"] for f in plain.json()["version"]["findings"]]
    assert any("direction role" in m for m in messages) and any("devil role" in m for m in messages)
    assert plain.json()["version"]["direction"] is None
    assert plain.json()["version"]["devils_advocacy"] is None
    assert plain.json()["version"]["status"] == "ready"

    async with container.session_factory() as session:
        profiles = container.repositories(session).llm_profiles
        for profile in await profiles.list_all():
            await profiles.delete(profile.id)
        await session.commit()
    await seed_legacy_profile(container, FULL_PROFILE)

    # A direction call that fails, then an advocate that fails: both recorded as warnings.
    container.llm = ScriptedGateway("!offline", json.dumps(good_body()), "!down")
    failing = await client.post("/api/reports", json=ask, headers=bearer(token))
    assert failing.status_code == 201
    messages = [f["message"] for f in failing.json()["version"]["findings"]]
    assert "Direction call failed: offline" in messages and "Call failed: down" in messages
    assert failing.json()["version"]["status"] == "ready"

    # Unusable direction JSON and an advocate who smuggles in a URL: dropped, with warnings.
    leaky = {**ADVOCACY, "argument": "Read https://evil.example/x instead."}
    container.llm = ScriptedGateway("[]", json.dumps(good_body()), json.dumps(leaky))
    dropped = await client.post("/api/reports", json=ask, headers=bearer(token))
    messages = [f["message"] for f in dropped.json()["version"]["findings"]]
    assert any(m.startswith("Direction unusable") for m in messages)
    assert "Discarded: it contained a URL" in messages
    assert dropped.json()["version"]["devils_advocacy"] is None

    # Two empty drafts fail generation: the advocate is never called.
    gateway = ScriptedGateway(
        json.dumps(DIRECTION),
        json.dumps(good_body(key_judgements=[])),
        json.dumps(good_body(key_judgements=[])),
    )
    container.llm = gateway
    empty = await client.post("/api/reports", json=ask, headers=bearer(token))
    assert empty.status_code == 201
    assert [r.schema_name for r in gateway.requests] == [
        "direction",
        "report",
        "report",
        "claim_proposals",
    ]
    assert empty.json()["version"]["status"] == "failed"
