"""Shared report fixtures: a body that passes the validator, ready to be varied."""

from __future__ import annotations

from typing import Any

GOOD_BODY = {
    "key_judgements": [
        {
            "id": "KJ1",
            "statement": "We assess it is highly likely that fighting around El Fasher will intensify over the next two weeks.",  # noqa: E501
            "probability": "highly_likely",
            "confidence": "moderate",
            "confidence_statement": "Information base: 3 items from 2 organisations. Rigour: alternatives considered. Volatility: high.",  # noqa: E501
            "supporting_evidence": ["E1", "E2"],
            "contradicting_evidence": [],
            "assumptions": ["A1"],
            "change_from_previous": None,
            "indicators": ["Reinforcement columns on the Mellit road"],
        },
        {
            "id": "KJ2",
            "statement": "We judge it is unlikely that a ceasefire holds beyond the month.",
            "probability": "unlikely",
            "confidence": "low",
            "confidence_statement": "Single reporting line; no instrument data.",
            "supporting_evidence": ["E3"],
            "contradicting_evidence": ["E9"],
            "assumptions": [],
            "indicators": [],
        },
    ],
    "reporting": [
        {
            "theme": "Ground activity",
            "items": [
                {
                    "text": "RSF forces entered El Fasher on 3 September.",
                    "evidence": ["E1"],
                    "grade": "B2",
                },
                {
                    "text": "Artillery fire was reported overnight.",
                    "evidence": ["E2"],
                    "grade": "C3",
                },
            ],
        }
    ],
    "assessment": [
        {"heading": "Trajectory", "text": "The siege is entering a new phase.", "evidence": ["E1"]}
    ],
    "assumptions": [
        {"id": "A1", "text": "Supply lines from the west stay open.", "lynchpin": True}
    ],
    "alternative_hypotheses": [
        {
            "text": "A negotiated pause.",
            "why_less_likely": "No mediator is active.",
            "evidence": ["E3"],
        }
    ],
    "indicators_and_warning": {
        "watch_condition": "elevated",
        "changes": ["More hotspots north of the city"],
    },
    "gaps": [
        {"eei": "EEI-2.1", "text": "No reporting on the eastern road."},
        {"text": "Casualty figures.", "eei": None},
    ],
    "collection_recommendations": ["Task FIRMS review of the northern approaches."],
    "sourcing_statement": "Three items from two independent organisations; syndicated copies counted once.",  # noqa: E501
    "unexpected": "dropped",
}


def good_body(**overrides: Any) -> dict[str, Any]:
    return {**GOOD_BODY, **overrides}
