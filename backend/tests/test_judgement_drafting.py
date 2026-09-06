"""Drafting never imposes the whole retrieval pool's confidence on every judgement."""

import json
from copy import deepcopy
from dataclasses import replace
from uuid import uuid4

import pytest

from ase.application.reports.drafting import draft_body
from ase.application.reports.templates import TEMPLATES
from ase.domain.doctrine import Confidence
from ase.domain.evidence import quality_of_information
from ase.domain.llm import LlmProfile, LlmRole
from ase.domain.reports import ReportHeader
from evidence_matrix_helpers import item
from feeds_helpers import NOW
from report_helpers import GOOD_BODY, ScriptedGateway


@pytest.mark.parametrize("language,style", [("en", "assessment"), ("fr", "briefing")])
async def test_low_bundle_summary_cannot_lower_a_strong_judgements_own_limit(language, style):
    evidence = [item("E1", "A1"), item("E2", "B1"), item("E3", "F6")]
    data = deepcopy(GOOD_BODY)
    data["key_judgements"][0]["confidence"] = "high"
    data["key_judgements"][1]["confidence"] = "high"
    gateway = ScriptedGateway(json.dumps(data))
    profile = LlmProfile(
        uuid4(),
        "Scripted",
        "http://localhost:11434/v1",
        "test",
        "encrypted",
        "hint",
        frozenset({LlmRole.ASSESSMENT}),
        2000,
        0.1,
        True,
        NOW,
        NOW,
    )
    quality = replace(quality_of_information(evidence), confidence_ceiling=Confidence.LOW)
    result = await draft_body(
        gateway,
        profile,
        "synthetic-key",
        TEMPLATES["intsum"],
        ReportHeader(
            "intsum", "Test", {"report_language": language, "report_style": style}, NOW, NOW, NOW
        ),
        None,
        quality,
        evidence,
        (),
    )
    assert result.body is not None and not result.has_errors
    assert result.body.key_judgements[0].confidence is Confidence.HIGH
    assert result.body.key_judgements[1].confidence is Confidence.LOW
    assert (
        "Confidence may not exceed low for any judgement"
        not in gateway.requests[0].messages[1].content
    )

    assert (
        "concise briefing" if style == "briefing" else "detailed assessment"
    ) in gateway.requests[0].messages[0].content
    assert (
        "narrative sections in French"
        if language == "fr"
        else "narrative sections in British English"
    ) in gateway.requests[0].messages[0].content
