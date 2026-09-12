"""Deterministic, source-backed figures for the professional report product."""

from __future__ import annotations

import io
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ase.domain.report_documents import DocumentFigure
from ase.domain.reports import KeyJudgement, ReportBody

WIDTH = 1440
MIN_HEIGHT = 620
MAX_JUDGEMENTS = 6
MAX_REFERENCES = 12
MAX_LABEL_CHARS = 120
FONT_DIRECTORY = Path(__file__).resolve().parents[2] / "adapters" / "reports" / "fonts"


@dataclass(frozen=True, slots=True)
class FigureJudgement:
    label: str
    statement: str
    assessment: str
    supporting: tuple[int, ...]
    contradicting: tuple[int, ...]


def _clean_label(value: str) -> str:
    printable = "".join(character if character.isprintable() else " " for character in value)
    return re.sub(r"\s+", " ", printable).strip()[:MAX_LABEL_CHARS]


def _numbers(labels: Sequence[str], citation_numbers: Mapping[str, int]) -> tuple[int, ...]:
    return tuple(
        dict.fromkeys(citation_numbers[label] for label in labels if label in citation_numbers)
    )


def _graph(
    body: ReportBody, citation_numbers: Mapping[str, int]
) -> tuple[tuple[FigureJudgement, ...], tuple[int, ...]] | None:
    candidates: list[FigureJudgement] = []
    for index, judgement in enumerate(body.key_judgements, start=1):
        supporting = _numbers(judgement.supporting_evidence, citation_numbers)
        contradicting = _numbers(judgement.contradicting_evidence, citation_numbers)
        if not supporting and not contradicting:
            continue
        candidates.append(
            FigureJudgement(
                f"KJ {index}",
                _clean_label(judgement.statement) or "Assessment statement unavailable",
                _assessment(judgement),
                supporting,
                contradicting,
            )
        )
    candidates = candidates[:MAX_JUDGEMENTS]
    all_references = tuple(
        dict.fromkeys(
            number
            for judgement in candidates
            for number in (*judgement.supporting, *judgement.contradicting)
        )
    )
    if len(candidates) < 2 or len(all_references) < 3:
        return None
    shared_references = {
        number
        for number in all_references
        if sum(
            number in (*judgement.supporting, *judgement.contradicting) for judgement in candidates
        )
        > 1
    }
    if not shared_references and not any(item.contradicting for item in candidates):
        return None
    selected_references = all_references[:MAX_REFERENCES]
    included = set(selected_references)
    selected: list[FigureJudgement] = []
    for candidate in candidates:
        supporting = tuple(number for number in candidate.supporting if number in included)
        contradicting = tuple(number for number in candidate.contradicting if number in included)
        if not supporting and not contradicting:
            continue
        selected.append(
            FigureJudgement(
                candidate.label,
                candidate.statement,
                candidate.assessment,
                supporting,
                contradicting,
            )
        )
    if len(selected) < 2:
        return None
    return tuple(selected), selected_references


def _assessment(judgement: KeyJudgement) -> str:
    probability = judgement.probability.value.replace("_", " ").capitalize()
    confidence = judgement.confidence.value.capitalize()
    return f"{probability} | {confidence} confidence"


@lru_cache(maxsize=64)
def _fonts() -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    regular = FONT_DIRECTORY / "DejaVuLGCSans.ttf"
    bold = FONT_DIRECTORY / "DejaVuLGCSans-Bold.ttf"
    return (
        ImageFont.truetype(str(regular), 22),
        ImageFont.truetype(str(bold), 24),
        ImageFont.truetype(str(bold), 17),
    )


def _ellipsise(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int
) -> str:
    if draw.textlength(text, font=font) <= width:
        return text
    suffix = "..."
    value = text
    while value and draw.textlength(value + suffix, font=font) > width:
        value = value[:-1]
    return value.rstrip() + suffix


def _positions(count: int, top: int, bottom: int) -> tuple[int, ...]:
    if count == 1:
        return ((top + bottom) // 2,)
    step = (bottom - top) / (count - 1)
    return tuple(round(top + step * index) for index in range(count))


def _curve(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
    distance = max(130, (end[0] - start[0]) // 2)
    points: list[tuple[int, int]] = []
    for index in range(25):
        t = index / 24
        inverse = 1 - t
        x = (
            inverse**3 * start[0]
            + 3 * inverse**2 * t * (start[0] + distance)
            + 3 * inverse * t**2 * (end[0] - distance)
            + t**3 * end[0]
        )
        y = (
            inverse**3 * start[1]
            + 3 * inverse**2 * t * start[1]
            + 3 * inverse * t**2 * end[1]
            + t**3 * end[1]
        )
        points.append((round(x), round(y)))
    return points


@lru_cache(maxsize=64)
def _render(judgements: tuple[FigureJudgement, ...], references: tuple[int, ...]) -> bytes:
    height = max(MIN_HEIGHT, 230 + max(len(references) * 58, len(judgements) * 104))
    image = Image.new("RGB", (WIDTH, height), "#F4F7F9")
    draw = ImageDraw.Draw(image)
    regular, bold, small_bold = _fonts()
    draw.rectangle((0, 0, WIDTH, 82), fill="#101820")
    draw.text((58, 25), "EVIDENCE RELATIONSHIP MAP", font=bold, fill="#FFFFFF")
    draw.text((58, 112), "RETAINED EVIDENCE", font=small_bold, fill="#53616D")
    draw.text((790, 112), "KEY JUDGEMENTS", font=small_bold, fill="#53616D")
    top, bottom = 182, height - 104
    source_y = dict(zip(references, _positions(len(references), top, bottom), strict=True))
    judgement_y = _positions(len(judgements), top, bottom)
    support_colour, contrary_colour = "#168A9B", "#C65D23"
    for judgement, target_y in zip(judgements, judgement_y, strict=True):
        for number in judgement.supporting:
            draw.line(
                _curve((352, source_y[number]), (752, target_y)), fill=support_colour, width=5
            )
        for number in judgement.contradicting:
            points = _curve((352, source_y[number]), (752, target_y))
            for start in range(0, len(points) - 1, 4):
                draw.line(points[start : start + 3], fill=contrary_colour, width=5)
    for number, y in source_y.items():
        draw.rounded_rectangle(
            (62, y - 24, 352, y + 24), radius=10, fill="#FFFFFF", outline="#B8C3CC", width=2
        )
        draw.ellipse((80, y - 9, 98, y + 9), fill=support_colour)
        draw.text((116, y - 14), f"REFERENCE [{number}]", font=small_bold, fill="#101820")
    for judgement, y in zip(judgements, judgement_y, strict=True):
        draw.rounded_rectangle(
            (752, y - 43, 1378, y + 43), radius=12, fill="#FFFFFF", outline="#9AA8B3", width=2
        )
        draw.text((776, y - 30), judgement.label, font=small_bold, fill="#168A9B")
        statement = _ellipsise(draw, judgement.statement, regular, 455)
        draw.text((872, y - 34), statement, font=regular, fill="#101820")
        draw.text((872, y + 5), judgement.assessment, font=small_bold, fill="#667581")
    legend_y = height - 58
    draw.line((58, legend_y, 110, legend_y), fill=support_colour, width=5)
    draw.text((124, legend_y - 12), "Supports", font=small_bold, fill="#53616D")
    draw.line((260, legend_y, 280, legend_y), fill=contrary_colour, width=5)
    draw.line((292, legend_y, 312, legend_y), fill=contrary_colour, width=5)
    draw.text((326, legend_y - 12), "Contradicts", font=small_bold, fill="#53616D")
    output = io.BytesIO()
    image.save(output, format="PNG", compress_level=6)
    return output.getvalue()


def _relationship_text(judgements: Sequence[FigureJudgement]) -> str:
    relationships: list[str] = []
    for judgement in judgements:
        if judgement.supporting:
            refs = ", ".join(str(number) for number in judgement.supporting)
            relationships.append(f"{judgement.label} is supported by references {refs}")
        if judgement.contradicting:
            refs = ", ".join(str(number) for number in judgement.contradicting)
            relationships.append(f"{judgement.label} is contradicted by references {refs}")
    return "; ".join(relationships)


def build_evidence_relationship_figure(
    body: ReportBody, citation_numbers: Mapping[str, int]
) -> DocumentFigure | None:
    """Build a bounded diagram when multiple judgements have a useful citation graph."""
    graph = _graph(body, citation_numbers)
    if graph is None:
        return None
    judgements, references = graph
    content = _render(judgements, references)
    height = max(MIN_HEIGHT, 230 + max(len(references) * 58, len(judgements) * 104))
    relationship_text = _relationship_text(judgements)
    return DocumentFigure(
        title="Evidence relationship map",
        caption=(
            "Figure 1. Relationships between the report's key judgements and retained "
            "evidence. Solid lines support a judgement; orange broken lines contradict it."
        ),
        alt_text=f"Evidence relationship diagram. {relationship_text}.",
        content=content,
        media_type="image/png",
        width_px=WIDTH,
        height_px=height,
        citation_numbers=references,
    )
