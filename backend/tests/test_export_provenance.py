"""Exported source content cannot inject markup or silently lose its provenance."""

from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from ase.api.schemas_report_evidence import ReportEvidenceOut
from ase.application.reports.archiving import archive_evidence
from ase.application.reports.document import build_document
from ase.application.reports.export_text import plain_markdown, safe_url, timestamp
from ase.application.reports.frozen_header import frozen_period_line
from ase.application.reports.render import render_markdown
from report_documents_helpers import document_records


def test_markdown_treats_hostile_source_and_model_text_as_plain_text() -> None:
    record, version = document_records()
    hostile = 'Headline | [click](javascript:alert(1))\n# Forged heading\n<img src="file:///x">'
    source = replace(
        version.evidence[0],
        title=hostile,
        source_name=hostile,
        url="javascript:alert(1)",
        archive_url="https://good.test/)\n<img src=x>",
    )
    body = replace(version.body, sourcing_statement=hostile)
    markdown = render_markdown(record.header, body, (source,), version.quality)
    assert "\n# Forged heading" not in markdown
    assert "<img" not in markdown
    assert "[click](javascript:" not in markdown
    assert "[link](javascript:" not in markdown
    assert "\\|" in markdown


def test_markdown_links_cannot_break_out_of_the_destination() -> None:
    record, version = document_records()
    source = replace(version.evidence[0], url="https://example.org/a)b[c]?q=x(y)")
    markdown = render_markdown(record.header, version.body, (source,), version.quality)
    assert "https://example.org/a%29b%5Bc%5D?q=x%28y%29" in markdown


def test_reader_references_retain_titles_while_diagnostics_stay_in_supporting_data() -> None:
    record, version = document_records()
    source = replace(
        version.evidence[0],
        title="Original source title",
        title_en="English title",
        language="uk",
        geo_confidence="country",
        observed_at=version.created_at,
        story_id="topic-cluster-1",
        independence_key="Declared publisher",
    )
    revised = replace(version, evidence=(source,))
    markdown = render_markdown(record.header, revised.body, revised.evidence, revised.quality)
    document = build_document(record, revised)
    text = "\n".join(block.text for block in document.blocks)
    assert document.references[0].title == "English title"
    assert document.references[0].original_title == "Original source title"
    assert document.references[0].language == "uk"
    assert "English title" in text and "Original source title" in text
    for expected in (
        "Translation (unverified)",
        "Language: uk",
        "Location precision: country",
        "Observed:",
        "Captured:",
        source.content_hash,
        "Grade rationale:",
        "Declared organisation:",
        "topic-cluster-1",
    ):
        assert expected in markdown
        assert expected not in text


def test_legacy_missing_provenance_remains_in_supporting_data_not_reader_report() -> None:
    record, version = document_records()
    source = replace(
        version.evidence[0],
        language=None,
        geo_confidence=None,
        observed_at=None,
        title_en=None,
        story_id=None,
        independence_key="",
    )
    revised = replace(version, evidence=(source,))
    document = build_document(record, revised)
    text = "\n".join(block.text for block in document.blocks)
    assert document.references[0].language is None
    assert document.references[0].original_title is None
    assert "Location precision:" not in text
    assert "Observed:" not in text


async def test_delayed_archival_keeps_frozen_period_and_archives_advocacy_only_citations() -> None:
    record, version = document_records()
    original_header = next(
        line for line in version.markdown.splitlines() if line.startswith("Template:")
    )
    record.period_from += timedelta(days=30)
    record.period_to += timedelta(days=30)
    record.data_cutoff += timedelta(days=30)
    body = replace(
        version.body, key_judgements=(), reporting=(), assessment=(), alternative_hypotheses=()
    )
    source = replace(version.evidence[0], archive_url=None)
    version = replace(version, body=body, evidence=(source,))
    repository, uow, archiver = AsyncMock(), AsyncMock(), AsyncMock()
    repository.get.return_value = record
    archiver.archive.return_value = (
        "https://web.archive.org/web/20260905/https://example.org/report"
    )
    count = await archive_evidence(archiver, repository, uow, version)
    assert count == 1
    exported = repository.set_archives.await_args.args[2]
    assert original_header in exported
    assert "2026-10-05" not in exported
    assert "NEEDS REVIEW" in exported
    uow.commit.assert_awaited_once()


@pytest.mark.parametrize(
    "url",
    [
        None,
        "",
        "javascript:alert(1)",
        "data:text/html,x",
        "file:///etc/passwd",
        "https://user:password@example.org",
        "https://example.org:invalid",
        "https://example.org)forged",
        "https://example.org|forged",
        "https://[broken",
        "https://example.org/\nforged",
        "https://example.org/%0d%0aevil",
        "https://example.org/\\evil",
        "https://example.org/" + "x" * 4096,
    ],
)
def test_unsafe_urls_have_no_clickable_export_destination(url: str | None) -> None:
    assert safe_url(url) is None


def test_plain_markdown_disables_block_syntax_and_automatic_links() -> None:
    assert plain_markdown("1. item") == r"1\. item"
    assert plain_markdown("- item") == r"\- item"
    assert plain_markdown("www.example.org me@example.org") == r"www\.example.org me\@example.org"
    assert plain_markdown("https://example.org") == r"https\://example.org"
    assert safe_url("https://[::1]:8443/a") == "https://[::1]:8443/a"


def test_api_evidence_contract_keeps_nullable_legacy_provenance() -> None:
    _, version = document_records()
    item = replace(
        version.evidence[0],
        title_en="Translated",
        language="uk",
        observed_at=None,
        geo_confidence=None,
        story_id=None,
    )
    payload = ReportEvidenceOut.model_validate(item).model_dump(mode="json")
    assert payload["title_en"] == "Translated" and payload["language"] == "uk"
    assert payload["observed_at"] is None and payload["geo_confidence"] is None
    assert payload["story_id"] is None and isinstance(payload["flags"], list)
    assert payload["captured_at"].startswith("2026-")
    assert timestamp(version.created_at.replace(tzinfo=None)).endswith("(timezone unknown)")


def test_escaped_template_identifier_survives_repeated_frozen_header_rendering() -> None:
    record, version = document_records()
    record.template = "country_brief"
    for _ in range(3):
        version.markdown = render_markdown(
            record.header,
            version.body,
            version.evidence,
            version.quality,
            period_line=frozen_period_line(record, version)
            if "country" in version.markdown
            else None,
        )
        assert "Period 2026-09-03" in frozen_period_line(record, version)
        assert "unknown" not in frozen_period_line(record, version)


def test_typed_frozen_period_takes_priority_over_legacy_markdown_header() -> None:
    record, version = document_records()
    version = replace(
        version,
        period_from=version.created_at - timedelta(hours=6),
        period_to=version.created_at,
        data_cutoff=version.created_at,
    )
    assert "Period 2026-09-04 19:00" not in frozen_period_line(record, version)
    assert "Period 2026-09-04 18:00" in frozen_period_line(record, version)
