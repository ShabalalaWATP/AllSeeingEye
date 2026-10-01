"""Mention parsing is plain-text, bounded and never treats addresses or markup as handles."""

import pytest

from ase.domain.board_mentions import MAX_MENTIONS, mentioned_handles, snippet


def test_handles_are_distinct_lowercase_and_in_first_seen_order() -> None:
    text = "@Analyst, please ask @desk_lead.\n@analyst again (@DESK_LEAD) and @x12 and @ab"
    assert mentioned_handles(text) == ("analyst", "desk_lead", "x12")


@pytest.mark.parametrize(
    "text",
    [
        "mail lead@desk_lead.example",
        "@@analyst",
        "<b>@ab</b>",
        "@" + "a" * 33,
        "word@analyst",
        "no mentions here",
    ],
)
def test_addresses_markup_and_overlong_tokens_are_not_mentions(text: str) -> None:
    assert mentioned_handles(text) == ()


def test_markup_around_a_handle_stays_plain_text() -> None:
    # The handle is read from text; nothing renders or interprets the surrounding markup.
    assert mentioned_handles("<i>@analyst</i>") == ("analyst",)


def test_more_than_the_cap_of_distinct_handles_is_refused_but_repeats_are_not() -> None:
    allowed = " ".join(f"@user_{n}" for n in range(MAX_MENTIONS))
    assert len(mentioned_handles(allowed + " " + allowed)) == MAX_MENTIONS
    with pytest.raises(ValueError, match="up to 10"):
        mentioned_handles(allowed + " @one_more")


def test_snippet_is_single_line_and_bounded() -> None:
    assert snippet("Line one\n\n  line\ttwo") == "Line one line two"
    long = snippet("word " * 100)
    assert len(long) <= 160 and long.endswith("…")
