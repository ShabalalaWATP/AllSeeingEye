"""The Telegram preview parser: what it reads, what it caps, and what it refuses.

The fixtures are a trimmed capture of a real ``https://t.me/s/DeepStateUA`` response taken
on 16 September 2026 plus the failure shapes Telegram actually serves: a page with no
channel history (private, removed, or preview switched off), a history whose post markup
has been renamed, a history carrying another channel's posts, and a malformed document.
No test touches the network.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ase.adapters.feeds.telegram_preview import (
    MAX_DOCUMENT_CHARS,
    MAX_ELEMENT_DEPTH,
    MAX_EXCERPT_CHARS,
    MAX_POSTS,
    TelegramMarkupError,
    parse_channel_preview,
)

FIXTURES = Path(__file__).parent / "fixtures" / "feeds"


def fixture(name: str) -> str:
    return (FIXTURES / f"telegram_preview_{name}.html").read_text("utf-8")


def test_a_recorded_channel_preview_yields_plain_text_posts_with_permalinks() -> None:
    preview = parse_channel_preview(fixture("deepstateua"), "DeepStateUA")
    assert preview.title == "✙DeepState✙🇺🇦"
    assert [post.key for post in preview.posts] == ["DeepStateUA/23818", "DeepStateUA/23819"]
    first = preview.posts[0]
    assert first.number == 23818
    assert first.url == "https://t.me/DeepStateUA/23818"
    assert first.views == "196K"
    assert first.published_at is not None
    assert first.published_at.isoformat() == "2026-09-09T15:20:01+00:00"
    assert first.text.startswith("🔄 Мапу оновлено")
    assert "Степанівки" in first.text


def test_markup_never_survives_into_the_text_the_application_stores() -> None:
    preview = parse_channel_preview(fixture("deepstateua"), "DeepStateUA")
    for post in preview.posts:
        assert "<" not in post.text and ">" not in post.text
        assert "telesco.pe" not in post.text  # media urls are ignored, never collected
        assert "\n" not in post.text and "  " not in post.text


@pytest.mark.parametrize(
    ("name", "channel", "expected"),
    [
        ("no_history", "examplechannel", "no public channel history"),
        ("changed_markup", "examplechannel", "markup has probably changed"),
        ("other_channel", "examplechannel", "none belonged to this channel"),
    ],
)
def test_an_unreadable_page_is_refused_rather_than_reported_as_empty(
    name: str, channel: str, expected: str
) -> None:
    with pytest.raises(TelegramMarkupError) as caught:
        parse_channel_preview(fixture(name), channel)
    assert expected in str(caught.value)


def test_the_recorded_page_is_refused_when_it_is_asked_for_another_channel() -> None:
    # A mis-keyed registry entry must not silently attribute one channel's posts to another.
    with pytest.raises(TelegramMarkupError):
        parse_channel_preview(fixture("deepstateua"), "SomeOtherChannel")


def test_malformed_markup_yields_only_the_posts_that_are_genuinely_readable() -> None:
    preview = parse_channel_preview(fixture("malformed"), "examplechannel")
    assert [post.key for post in preview.posts] == ["examplechannel/1", "examplechannel/2"]
    unclosed, entities = preview.posts
    # An unclosed post is still bounded by its ancestor, and <br> becomes a space.
    assert unclosed.text == (
        "First post, never closed properly bold second line a link inside the post"
    )
    assert unclosed.published_at is None  # no usable timestamp is better than an invented one
    assert entities.text == "Second post & entities — kept as text"
    assert entities.published_at is None  # "not-a-date" is discarded, not guessed at
    assert entities.views == "12.3K"


def test_a_link_inside_a_post_contributes_its_text_and_never_its_target() -> None:
    preview = parse_channel_preview(fixture("malformed"), "examplechannel")
    assert "example.invalid" not in preview.posts[0].text
    assert "a link inside the post" in preview.posts[0].text


def test_an_oversized_document_is_refused_before_it_is_parsed() -> None:
    with pytest.raises(TelegramMarkupError, match="larger than this parser accepts"):
        parse_channel_preview("x" * (MAX_DOCUMENT_CHARS + 1), "examplechannel")


def test_deeply_nested_markup_is_refused_instead_of_exhausting_the_stack() -> None:
    body = "<div>" * (MAX_ELEMENT_DEPTH + 5)
    with pytest.raises(TelegramMarkupError, match="nested more deeply"):
        parse_channel_preview(f'<section class="tgme_channel_history">{body}', "examplechannel")


def _synthetic(channel: str, posts: int, text: str) -> str:
    messages = "".join(
        f'<div class="tgme_widget_message js-widget_message" data-post="{channel}/{index}">'
        f'<div class="tgme_widget_message_text js-message_text">{text}</div>'
        f'<a class="tgme_widget_message_date" href="https://t.me/{channel}/{index}">'
        f'<time datetime="2026-09-09T15:20:0{index % 10}+00:00"></time></a></div>'
        for index in range(1, posts + 1)
    )
    return f'<section class="tgme_channel_history">{messages}</section>'


def test_the_number_of_posts_taken_from_one_page_is_capped() -> None:
    preview = parse_channel_preview(_synthetic("examplechannel", 60, "text"), "examplechannel")
    assert len(preview.posts) == MAX_POSTS


def test_a_very_long_post_is_truncated_to_the_excerpt_limit() -> None:
    document = _synthetic("examplechannel", 1, "word " * 4000)
    text = parse_channel_preview(document, "examplechannel").posts[0].text
    assert len(text) == MAX_EXCERPT_CHARS
    assert text.endswith("…")
