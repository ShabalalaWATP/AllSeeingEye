"""Diagram data validation: valid shapes, oversized, unsupported and untraceable data."""

from __future__ import annotations

import json
from typing import Any

import pytest

from ase.application.reports.analysis import run_analysis
from ase.application.reports.diagram_svg import render_diagram_svg
from ase.application.reports.diagram_text import diagram_lines, project_diagram
from ase.application.reports.templates import template_for
from ase.domain.report_diagram_schema import parse_diagram
from ase.domain.report_diagrams import DiagramKind, DiagramRejected
from report_analysis_helpers import (
    ACTOR_MAP,
    CAUSAL_CHAIN,
    MATRIX,
    SERIES,
    TIMELINE,
    AnalysisGateway,
    analysis_inputs,
    analysis_payload,
    analysis_profile,
)

pytestmark = pytest.mark.anyio
LABELS = frozenset({"E1", "E2", "E3"})


@pytest.mark.parametrize(
    ("payload", "kind"),
    [
        (TIMELINE, DiagramKind.TIMELINE),
        (ACTOR_MAP, DiagramKind.ACTOR_MAP),
        (CAUSAL_CHAIN, DiagramKind.CAUSAL_CHAIN),
        (MATRIX, DiagramKind.COMPARISON_MATRIX),
        (SERIES, DiagramKind.QUANTITATIVE_SERIES),
    ],
)
def test_each_supported_shape_parses_and_stays_traceable(
    payload: dict[str, Any], kind: DiagramKind
) -> None:
    diagram = parse_diagram(payload, LABELS)
    assert diagram.kind is kind
    assert diagram.alt_text and diagram.evidence_labels()
    assert set(diagram.evidence_labels()) <= LABELS


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"kind": "pie_chart"}, "unsupported diagram kind"),
        ({"entries": TIMELINE["entries"][:2]}, "three and twelve entries"),
        ({"entries": [{**row, "evidence": []} for row in TIMELINE["entries"]]}, "cite evidence"),
        (
            {"entries": [{**row, "evidence": ["E9"]} for row in TIMELINE["entries"]]},
            "not in this report",
        ),
        ({"alt_text": ""}, "diagram text is empty"),
        ({"title": "x" * 200}, "length limit"),
        ({"title": "See https://example.org/story"}, "markup or links"),
        ({"alt_text": "A <script>alert(1)</script> diagram"}, "markup or links"),
        ({"nodes": ACTOR_MAP["nodes"]}, "cannot carry nodes"),
    ],
)
def test_an_unsupported_or_untraceable_diagram_is_refused(
    change: dict[str, Any], reason: str
) -> None:
    with pytest.raises(DiagramRejected) as error:
        parse_diagram({**TIMELINE, **change}, LABELS)
    assert reason in error.value.reason


def test_an_oversized_graph_is_refused() -> None:
    nodes = [
        {"id": f"N{index}", "label": f"Actor {index}", "detail": "", "evidence": ["E1"]}
        for index in range(1, 15)
    ]
    edges = [
        {"source": "N1", "target": f"N{index}", "label": "", "evidence": ["E1"]}
        for index in range(2, 15)
    ]
    with pytest.raises(DiagramRejected) as error:
        parse_diagram({**ACTOR_MAP, "nodes": nodes, "edges": edges}, LABELS)
    assert "three to twelve nodes" in error.value.reason


def test_a_graph_with_an_unattached_node_is_refused() -> None:
    nodes = [*ACTOR_MAP["nodes"], {"id": "N4", "label": "Spare", "detail": "", "evidence": ["E1"]}]
    with pytest.raises(DiagramRejected) as error:
        parse_diagram({**ACTOR_MAP, "nodes": nodes}, LABELS)
    assert "take part in a relationship" in error.value.reason


def test_series_values_must_be_finite_numbers_over_shared_periods() -> None:
    broken = {
        **SERIES,
        "series": [
            {**SERIES["series"][0]},
            {
                "label": "Second",
                "points": [{"label": "3 Sep", "value": 1}, {"label": "9 Sep", "value": 2}],
                "evidence": ["E3"],
            },
        ],
    }
    with pytest.raises(DiagramRejected):
        parse_diagram(broken, LABELS)


def test_the_equivalent_table_carries_everything_the_picture_shows() -> None:
    projection = project_diagram(parse_diagram(ACTOR_MAP, LABELS))
    assert projection.columns == ("From", "Relationship", "To", "Source")
    assert projection.rows[0][0] == ("Advancing force", "attacks", "City garrison (holding)")
    assert projection.rows[0][1] == ("E1",)
    lines = diagram_lines(parse_diagram(MATRIX, LABELS))
    assert lines[2].startswith("Two accounts compared")
    assert "| Ground advance | One agency | City centre | E1 |" in lines


@pytest.mark.parametrize("payload", [TIMELINE, ACTOR_MAP, CAUSAL_CHAIN, MATRIX, SERIES])
def test_the_drawing_is_deterministic_escaped_and_carries_its_text(
    payload: dict[str, Any],
) -> None:
    diagram = parse_diagram(payload, LABELS)
    svg = render_diagram_svg(diagram)
    assert svg == render_diagram_svg(diagram)
    assert svg.startswith("<svg ") and svg.endswith("</svg>")
    assert f"<desc>{diagram.alt_text}</desc>" in svg
    assert "script" not in svg and "href" not in svg


def test_the_drawing_escapes_source_text_rather_than_emitting_markup() -> None:
    diagram = parse_diagram(
        {
            **TIMELINE,
            "entries": [
                {"when": "3 Sep", "label": 'A & B "joint" report', "evidence": ["E1"]},
                *TIMELINE["entries"][1:],
            ],
        },
        LABELS,
    )
    svg = render_diagram_svg(diagram)
    assert "&amp;" in svg and "A & B" not in svg


async def test_a_refused_diagram_is_recorded_and_never_half_drawn() -> None:
    header, body, evidence = analysis_inputs()
    broken = {**TIMELINE, "entries": [{**TIMELINE["entries"][0], "evidence": ["E99"]}]}
    outcome = await run_analysis(
        AnalysisGateway(analysis_payload(broken)),
        analysis_profile(),
        "key",
        template_for("intsum"),
        header,
        body,
        evidence,
    )
    assert outcome.performed and outcome.diagram is None
    assert outcome.diagram_reason
    assert [row.rule for row in outcome.findings] == ["diagram"]
    assert outcome.apply(body).diagrams == ()


async def test_an_accepted_diagram_reaches_the_body_once() -> None:
    header, body, evidence = analysis_inputs()
    outcome = await run_analysis(
        AnalysisGateway(analysis_payload(TIMELINE)),
        analysis_profile(),
        "key",
        template_for("intsum"),
        header,
        body,
        evidence,
    )
    extended = outcome.apply(body)
    assert len(extended.diagrams) == 1
    assert set(extended.diagrams[0].evidence_labels()) <= extended.cited_labels()


async def test_a_diagram_request_that_is_not_an_object_is_refused_without_failing_the_pass() -> (
    None
):
    header, body, evidence = analysis_inputs()
    payload = json.dumps(
        {"sections": [{"heading": "A", "text": "B", "evidence": ["E1"]}], "diagram": "draw a map"}
    )
    outcome = await run_analysis(
        AnalysisGateway(payload),
        analysis_profile(),
        "key",
        template_for("intsum"),
        header,
        body,
        evidence,
    )
    assert not outcome.performed and outcome.apply(body) == body
