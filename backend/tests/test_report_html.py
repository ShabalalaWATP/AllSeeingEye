"""Semantic HTML preserves frozen text and only isolates structured fields."""

from dataclasses import replace
from html.parser import HTMLParser

import pytest

from ase.adapters.reports import html_document
from ase.adapters.reports.html_document import render_html
from ase.application.reports.document import DocumentBuilder, build_document
from ase.domain.errors import InvalidRequest
from ase.domain.report_documents import BlockKind, DocumentBlock, DocumentInline, ReportDocument
from report_documents_helpers import document_records


class Inspection(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags, self.blocks, self.isolates, self.text = [], [], [], []
        self.current = self.isolate = None

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag in {"h1", "h2", "h3", "p"}:
            self.current = ""
        if tag == "bdi":
            self.isolate = [dict(attrs)["dir"], ""]

    def handle_data(self, data):
        self.text.append(data)
        if self.current is not None:
            self.current += data
        if self.isolate is not None:
            self.isolate[1] += data

    def handle_endtag(self, tag):
        if tag == "bdi":
            self.isolates.append(tuple(self.isolate))
            self.isolate = None
        if tag in {"h1", "h2", "h3", "p"}:
            self.blocks.append(self.current)
            self.current = None


def inspect(document):
    parsed = Inspection()
    parsed.feed(render_html(document).decode("utf-8"))
    return parsed


@pytest.mark.parametrize("language", ["ar", "fa"])
def test_report_preserves_mixed_script_text_and_structured_citations(language):
    record, version = document_records()
    statement = "پژوهش‌گر فارسی ۱۲۳؛ النَّصّ العربي ١٢٣ [E99] https://example.test/literal"
    record.scope = {"report_language": language, "question": statement}
    first = replace(
        version.body.key_judgements[0], statement=statement, supporting_evidence=("E1", "E2")
    )
    version = replace(version, body=replace(version.body, key_judgements=(first,)))
    document = build_document(record, version)
    parsed = inspect(document)
    assert statement in "".join(parsed.text)
    assert ("ltr", "[1, 2]") in parsed.isolates
    assert any(direction == "auto" and statement in text for direction, text in parsed.isolates)
    assert ("ltr", "[E99]") not in parsed.isolates
    assert any(
        tag == "a" and attrs.get("href") == version.evidence[0].url for tag, attrs in parsed.tags
    )
    assert ("html", {"lang": language, "dir": "rtl"}) in parsed.tags


def test_malicious_content_cannot_create_resources_or_attributes():
    attack = '<script>fetch("https://evil.test")</script><img src="file:///secret">&'
    doc = ReportDocument(
        attack,
        "reference",
        (DocumentBlock(BlockKind.TEXT, attack, (DocumentInline(attack, "ltr"),)),),
        '" onload="attack',
    )
    parsed = inspect(doc)
    assert parsed.blocks == [attack]
    assert all(
        tag not in {"script", "img", "a", "iframe", "link", "base", "object", "form"}
        for tag, _ in parsed.tags
    )
    assert all(
        not name.startswith("on") and name not in {"href", "src"}
        for _, attrs in parsed.tags
        for name in attrs
    )
    assert ("html", {"lang": "und", "dir": "ltr"}) in parsed.tags
    csp = next(
        attrs["content"] for tag, attrs in parsed.tags if tag == "meta" and "http-equiv" in attrs
    )
    assert "default-src 'none'" in csp and "base-uri 'none'" in csp


def test_inline_projection_and_bounds():
    with pytest.raises(ValueError, match="projection"):
        DocumentBlock(BlockKind.TEXT, "original", (DocumentInline("different"),))
    with pytest.raises(ValueError, match="256"):
        DocumentBlock(BlockKind.TEXT, "", (DocumentInline(""),) * 257)
    with pytest.raises(ValueError):
        DocumentInline("text", '" onclick="attack')
    builder = DocumentBuilder()
    builder.inline((DocumentInline("a\x00"), DocumentInline("ب\u200c", "rtl")))
    assert builder.blocks[0].text == "aب\u200c"
    assert "".join(run.text for run in builder.blocks[0].inlines) == builder.blocks[0].text
    with pytest.raises(InvalidRequest):
        render_html(
            ReportDocument("title", "reference", (DocumentBlock(BlockKind.TEXT, "a" * 16001),))
        )
    with pytest.raises(InvalidRequest):
        render_html(
            ReportDocument("title", "reference", (DocumentBlock(BlockKind.TEXT, ""),) * 2001)
        )


def test_encoded_byte_limit(monkeypatch):
    monkeypatch.setattr(html_document, "MAX_HTML_BYTES", 100)
    with pytest.raises(InvalidRequest, match="byte"):
        render_html(ReportDocument("title", "reference", (DocumentBlock(BlockKind.TEXT, "<>&"),)))
