"""STIX rebinds only the canonical metadata wrapper, preserving frozen narrative."""

import json
from dataclasses import replace
from uuid import uuid4

import pytest

from ase.adapters.reports.stix import FrozenStixRenderer
from ase.domain.stix import StixTlp
from test_stix_export import cyber_records


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_copied_canonical_header_uses_current_identity_without_rewriting_citations(newline):
    record, version = cyber_records()
    source_id = uuid4()
    narrative = (
        "## What happened\n\nFrozen assessment [1](#reference-1).\n\n"
        f"An explicit citation to report {source_id} stays substantive content.\n"
        f"Report {source_id} \\| version 6\n"
    ).replace("\n", newline)
    markdown = newline.join(("# Frozen title", "", f"Report {source_id} \\| version 6", "", ""))
    markdown += narrative
    copied = replace(version, number=1, markdown=markdown)
    content = FrozenStixRenderer().render(record, copied, StixTlp.AMBER)
    report = next(row for row in json.loads(content)["objects"] if row["type"] == "report")
    exported = report["description"].split("apply.\n\n", 1)[1]
    assert exported == markdown.replace(
        f"Report {source_id} \\| version 6", f"Report {record.id} \\| version 1", 1
    )
    assert exported.endswith(narrative)
    assert copied.markdown == markdown
    assert FrozenStixRenderer().render(record, copied, StixTlp.AMBER) == content


def test_personal_canonical_header_is_preserved_exactly():
    record, version = cyber_records()
    markdown = f"# Frozen title\n\nReport {record.id} \\| version 1\n\nFrozen narrative.\n"
    result = FrozenStixRenderer().render(record, replace(version, markdown=markdown), StixTlp.GREEN)
    report = next(row for row in json.loads(result)["objects"] if row["type"] == "report")
    assert report["description"].endswith(markdown)


@pytest.mark.parametrize(
    "markdown",
    [
        "# Legacy report\n\nFrozen legacy narrative.\n",
        "# Report\n\nReport an incident | version unknown\n",
        "# Report\n\nReport 12345678-1234-1234-1234-123456789abc | version 6\n\nNarrative.",
        "# Report\n\nReport 12345678-1234-1234-1234-123456789abc \\| version 0\n\nNarrative.",
        "# Report\n\nReport not-a-report-id \\| version 6\n\nNarrative.",
        "# Report\n\nA source writes:\nReport 12345678-1234-1234-1234-123456789abc \\| version 6\n",
    ],
)
def test_noncanonical_or_narrative_metadata_is_not_rewritten(markdown):
    record, version = cyber_records()
    result = FrozenStixRenderer().render(record, replace(version, markdown=markdown), StixTlp.RED)
    report = next(row for row in json.loads(result)["objects"] if row["type"] == "report")
    assert report["description"].endswith(markdown)
