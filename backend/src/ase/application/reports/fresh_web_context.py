"""Bound the public question scope sent to generated web discovery."""

import json

from ase.domain.research import ResearchQuery


def web_query_context(query: ResearchQuery) -> str | None:
    area = query.area.geometry.to_collection() if query.area else None
    context = json.dumps(
        {
            "question": query.question,
            "subject": query.subject,
            "countries": query.country_isos,
            "languages": query.languages,
            "since_inclusive": query.since.isoformat(),
            "until_exclusive": query.until.isoformat(),
            "area_geojson": area,
            "scope_notice": "Search scope only; dates and spatial matches require verification.",
        },
        ensure_ascii=False,
    )
    return context if len(context) <= 12000 else None
