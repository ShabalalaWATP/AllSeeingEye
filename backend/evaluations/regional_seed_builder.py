"""Build reproducible fictional regional seeds, never live or human-reviewed facts."""

import json
from pathlib import Path

REGIONS = {
    "ru": ("Russia", "ru", "Поставка не подтверждена.", "Delivery is not confirmed."),
    "cn": ("China", "zh-Hant", "尚未確認交付。", "Delivery has not yet been confirmed."),
    "ir": ("Iran", "fa", "تحویل تأیید نشده است.", "Delivery has not been confirmed."),
}


def cases() -> list[dict[str, object]]:
    """Four distinct failure modes per region, with deliberately fictional entities."""
    output: list[dict[str, object]] = []
    for region, (country, language, original, translation) in REGIONS.items():
        scenarios = {
            "official_claim": (
                "Does the fictional ministry statement establish delivery?",
                "A fictional ministry says Project Juniper delivered 12 sensors.",
                "An independent fictional inventory records 12 sensors ordered, none received.",
                "The sources disagree about delivery; an order is not a receipt.",
                "The delivery was independently confirmed or political affiliation proves truth.",
            ),
            "identity": (
                "Are the two fictional Juniper companies the same legal entity?",
                "Juniper Example Ltd has registry identifier TEST-A and jurisdiction A.",
                "Juniper Example Ltd has registry identifier TEST-B and jurisdiction B.",
                "The identical names identify candidates with different registry identifiers.",
                "The entities are merged or ownership is inferred from the shared name.",
            ),
            "language": (
                "Does the original-language bulletin confirm delivery?",
                original,
                "An English aggregator incorrectly paraphrases the bulletin as delivery confirmed.",
                f"The original statement means: {translation}",
                "Negation is dropped, or an aggregator copy counts as independent confirmation.",
            ),
            "geography": (
                "Where can the fictional service interruption be located?",
                f"A fictional bulletin mentions an interruption somewhere in {country}; "
                "no location is supplied.",
                "The publisher's contact page lists a capital-city office, "
                "not an incident location.",
                "The event has country-level context only; publisher location is a different role.",
                "The event is placed at the country centroid, "
                "publisher office or zero coordinates.",
            ),
        }
        for kind, (question, first, second, fact, forbidden) in scenarios.items():
            identifier = f"{region}_{kind}"
            events = [
                {
                    "key": key,
                    "source": source,
                    "title": title,
                    "summary": title,
                    "language": language if kind == "language" and key == "original" else "en",
                    "published_at": "2026-09-05T10:00:00Z",
                    "reliability": "F",
                }
                for key, source, title in (
                    ("original", "fixture_origin", first),
                    ("context", "fixture_context", second),
                )
            ]
            output.append(
                {
                    "id": identifier,
                    "title": f"{country}: synthetic {kind.replace('_', ' ')}",
                    "question": question,
                    "as_of": "2026-09-06T12:00:00Z",
                    "sources": [
                        {
                            "id": "fixture_origin",
                            "name": "Fictional original publisher",
                            "organisation": "fixture_origin",
                        },
                        {
                            "id": "fixture_context",
                            "name": "Fictional context publisher",
                            "organisation": "fixture_origin"
                            if kind == "language"
                            else "fixture_context",
                        },
                    ],
                    "events": events,
                    "reference": {
                        "label_origin": "Assistant-authored synthetic development seed, 2026-09-06",
                        "human_review_status": "pending",
                        "reference_facts": [fact],
                        "required_event_keys": ["original", "context"],
                        "counterevidence_event_keys": ["context"],
                        "required_caveats": [
                            "Fictional fixture, no real-world allegation.",
                            "Source and information uncertainty must remain explicit.",
                        ],
                        "forbidden_inferences": [forbidden],
                        "expected_declared_organisation_groups": 1 if kind == "language" else 2,
                    },
                    "replay": {
                        "initial": [{"id": "seed", "event_keys": ["original"]}],
                        "challenge": [{"id": "context", "event_keys": ["context"]}],
                    },
                }
            )
    return output


if __name__ == "__main__":
    destination = Path(__file__).parent / "regional_cases"
    destination.mkdir(exist_ok=True)
    for case in cases():
        (destination / f"{case['id']}.json").write_bytes(
            (json.dumps(case, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        )
