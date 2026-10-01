"""KAN-36: plain-text and unchanged-record fast paths in the feed pipeline."""

from __future__ import annotations

import random
import unicodedata
from html import unescape
from html.parser import HTMLParser

import pytest

from ase.application.feeds import pipeline
from ase.application.feeds.pipeline import Normaliser, clean_text, strip_html
from ase.domain.events import MAX_SUMMARY, MAX_TITLE, content_hash
from feeds_helpers import make_event

# Characters chosen to stress every step of clean_text: str.strip and \s differences
# (\x1c-\x1f, \x85, \xa0, U+2028, U+3000), control characters, NFC composition,
# astral code points and every markup trigger.
_PLAIN = [
    "a", "Z", "7", " ", "  ", "\t", "\n", "\r", "\r\n", "\x0b", "\x0c", "\x1c", "\x1f",
    "\x85", "\xa0", chr(0x2028), chr(0x3000), "\x00", "\x07", "\x7f",
    chr(0xE9), "e" + chr(0x301), chr(0x212B), chr(0xDF), chr(0xFB01),
    chr(0x65E5) + chr(0x672C), chr(0x1F600), chr(0x2026),
    ";", "#", ">", "\"", "'", "/", "=",
]  # fmt: skip
_MARKUP = [
    "<", "&", "<b>", "</b>", "<p class='x'>", "<br/>", "<!-- note -->", "<script>x</script>",
    "&amp;", "&lt;b&gt;", "&#39;", "&#x41;", "&nbsp;", "&bogus;", "&amp", "&lt;", "<!DOCTYPE html>",
    "<?xml?>", "< b", "a<", "&#0;", "&#x1F600;",
]  # fmt: skip


class _ReferenceExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def _reference_strip_html(value: str | None) -> str | None:
    """The original parser-only implementation, kept verbatim as the oracle."""
    if not value:
        return None
    extractor = _ReferenceExtractor()
    extractor.feed(unescape(value))
    extractor.close()
    return " ".join(extractor.parts) or None


def _reference_clean_text(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    text = _reference_strip_html(value) or ""
    text = unicodedata.normalize("NFC", pipeline._CONTROL.sub("", text))
    text = pipeline._WHITESPACE.sub(" ", text).strip()
    if not text:
        return None
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def _samples(count: int, *, markup: bool, seed: int) -> list[str]:
    rng = random.Random(seed)  # noqa: S311 - reproducible test data, not security material
    alphabet = _PLAIN + _MARKUP if markup else _PLAIN
    return ["".join(rng.choices(alphabet, k=rng.randint(0, 40))) for _ in range(count)]


_FIXED = ["", " ", "\n\t ", "plain", "  padded  ", "x\x1fy", "\x1c", "\xa0\xa0", "e" + chr(0x301)]
_PLAIN_SAMPLES = _FIXED + _samples(3_000, markup=False, seed=36)
_MIXED_SAMPLES = _samples(3_000, markup=True, seed=3636)


def test_plain_samples_take_the_fast_path_and_markup_samples_do_not() -> None:
    assert all("<" not in s and "&" not in s for s in _PLAIN_SAMPLES)
    assert sum("<" in s or "&" in s for s in _MIXED_SAMPLES) > 2_500


@pytest.mark.parametrize("samples", [_PLAIN_SAMPLES, _MIXED_SAMPLES], ids=["plain", "mixed"])
def test_strip_html_matches_the_full_parser(samples: list[str]) -> None:
    for value in samples:
        assert strip_html(value) == _reference_strip_html(value), repr(value)


@pytest.mark.parametrize("samples", [_PLAIN_SAMPLES, _MIXED_SAMPLES], ids=["plain", "mixed"])
@pytest.mark.parametrize("limit", [5, MAX_TITLE, MAX_SUMMARY])
def test_clean_text_matches_the_full_parser(samples: list[str], limit: int) -> None:
    for value in samples:
        assert clean_text(value, limit) == _reference_clean_text(value, limit), repr(value)


def test_none_is_preserved() -> None:
    assert strip_html(None) is None
    assert clean_text(None, MAX_TITLE) is None


def test_plain_text_never_builds_a_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse() -> None:
        raise AssertionError("plain text must not be parsed")

    monkeypatch.setattr(pipeline, "_TextExtractor", refuse)
    assert strip_html("  Vessel ÉCLAIR\tunder way  ") == "Vessel ÉCLAIR\tunder way"
    assert clean_text("  Vessel\n\nunder way ", MAX_TITLE) == "Vessel under way"
    with pytest.raises(AssertionError):
        strip_html("<b>bold</b>")


def test_unchanged_event_is_returned_as_the_same_object() -> None:
    event = make_event("same", title="Clean title", summary="Clean summary")
    assert event.content_hash
    [result] = Normaliser().process([event])
    assert result is event


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"title": "<b>Bold</b>  title"}, {"title": "Bold title"}),
        ({"summary": " padded\n summary "}, {"summary": "padded summary"}),
        ({"url": "  https://example.com/x  "}, {"url": "https://example.com/x"}),
        ({"url": "javascript:alert(1)"}, {"url": None}),
        ({"summary": "&lt;i&gt;"}, {"summary": None}),
    ],
)
def test_changed_event_is_copied_with_cleaned_fields(
    changes: dict[str, str], expected: dict[str, str | None]
) -> None:
    original = make_event("changed").with_changes(**changes)
    [result] = Normaliser().process([original])
    assert result is not original
    for field, value in expected.items():
        assert getattr(result, field) == value
    for field, value in changes.items():
        assert getattr(original, field) == value
    assert result.content_hash == original.content_hash
    assert result.id == original.id and result.attributes == original.attributes


def test_missing_hash_is_computed_on_a_copy() -> None:
    original = make_event("unhashed").with_changes(content_hash="")
    [result] = Normaliser().process([original])
    assert result is not original and original.content_hash == ""
    published = original.published_at.isoformat() if original.published_at else None
    assert result.content_hash == content_hash(
        original.title, original.summary, original.url, published
    )
