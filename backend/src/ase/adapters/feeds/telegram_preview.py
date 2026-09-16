"""Bounded parsing of a public Telegram channel web preview page (``https://t.me/s/<channel>``).

Telegram publishes no read API for public channels without an account, so this is the
only route to material that breaks there first. The preview is HTML, which the rest of
the application deliberately avoids reading, so parsing is defensive on purpose:

* one recognised page shape, checked before any post is trusted;
* hard caps on document size, element nesting, posts and excerpt characters;
* text only, taken from the post body element; media, thumbnails and link previews are
  ignored and never requested;
* an unrecognised shape raises :class:`TelegramMarkupError` rather than returning an
  empty or partly-parsed list, so a markup change can never look like a quiet channel.

The parser never follows a link, never resolves a relative URL and never emits raw HTML.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser

MAX_DOCUMENT_CHARS = 1_500_000
MAX_POSTS = 20
MAX_EXCERPT_CHARS = 700
# Per post, not per page, so one enormous post cannot starve the ones after it.
MAX_CAPTURED_CHARS = MAX_EXCERPT_CHARS * 8
MAX_MESSAGES = 200
MAX_ELEMENT_DEPTH = 200
MAX_CHANNEL_CHARS = 64
MAX_TITLE_CHARS = 140
# A view counter is one short token; anything longer means the element never closed.
MAX_VIEW_PARTS = 4
MAX_VIEW_CHARS = 24

HISTORY_CLASS = "tgme_channel_history"
MESSAGE_CLASS = "tgme_widget_message"
TEXT_CLASS = "tgme_widget_message_text"
VIEWS_CLASS = "tgme_widget_message_views"
DATE_CLASS = "tgme_widget_message_date"

# Elements that never carry an end tag, so they must not move the nesting depth.
_VOID = frozenset(
    {
        "area",
        "base",
        "basefont",
        "br",
        "col",
        "embed",
        "frame",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)


class TelegramMarkupError(ValueError):
    """The page is not a readable channel preview in the shape this parser understands."""


@dataclass(frozen=True, slots=True)
class TelegramPost:
    """One public channel post, reduced to plain text and its own permalink."""

    key: str
    number: int
    text: str
    published_at: datetime | None
    views: str | None

    @property
    def url(self) -> str:
        return f"https://t.me/{self.key}"


@dataclass(frozen=True, slots=True)
class TelegramPreview:
    channel: str
    title: str | None
    posts: tuple[TelegramPost, ...]


def _classes(attrs: list[tuple[str, str | None]]) -> frozenset[str]:
    for name, value in attrs:
        if name == "class" and value:
            return frozenset(value.split())
    return frozenset()


def _attribute(attrs: list[tuple[str, str | None]], name: str) -> str:
    for key, value in attrs:
        if key == name and value:
            return value
    return ""


def _timestamp(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)


def _collapse(parts: list[str], limit: int) -> str:
    text = " ".join("".join(parts).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


class _PreviewParser(HTMLParser):
    """A small explicit state machine; nothing is inferred from text position alone."""

    def __init__(self, channel: str) -> None:
        super().__init__(convert_charrefs=True)
        self._channel = channel.casefold()
        self.history_seen = False
        self.messages_seen = 0
        self.title: str | None = None
        # The newest posts are the useful ones, and the page lists them last.
        self.posts: deque[TelegramPost] = deque(maxlen=MAX_POSTS)
        self._stack: list[str] = []
        self._captured = 0
        self._message_depth: int | None = None
        self._text_depth: int | None = None
        self._views_depth: int | None = None
        self._date_depth: int | None = None
        self._key = ""
        self._parts: list[str] = []
        self._published: datetime | None = None
        self._dated: datetime | None = None
        self._views: list[str] = []

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._open(tag, attrs, depth=len(self._stack) + 1)
        if tag == "br" and self._text_depth is not None:
            self._parts.append(" ")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _VOID:
            self.handle_startendtag(tag, attrs)
            return
        if len(self._stack) >= MAX_ELEMENT_DEPTH:
            raise TelegramMarkupError("Channel preview markup is nested more deeply than expected")
        self._stack.append(tag)
        self._open(tag, attrs, depth=len(self._stack))

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID or tag not in self._stack:
            return
        while self._stack:
            closed = self._stack.pop()
            self._close(len(self._stack) + 1)
            if closed == tag:
                return

    def handle_data(self, data: str) -> None:
        if self._views_depth is not None and len(self._views) < MAX_VIEW_PARTS:
            self._views.append(data)
        if self._text_depth is None or self._captured >= MAX_CAPTURED_CHARS:
            return
        self._captured += len(data)
        self._parts.append(data)

    def _open(self, tag: str, attrs: list[tuple[str, str | None]], *, depth: int) -> None:
        if tag == "meta" and _attribute(attrs, "property") == "og:title" and self.title is None:
            self.title = _collapse([_attribute(attrs, "content")], MAX_TITLE_CHARS) or None
            return
        classes = _classes(attrs)
        if HISTORY_CLASS in classes:
            self.history_seen = True
        if self._message_depth is None:
            if MESSAGE_CLASS in classes and _attribute(attrs, "data-post"):
                self._begin_message(_attribute(attrs, "data-post"), depth)
            return
        if TEXT_CLASS in classes and self._text_depth is None:
            self._text_depth = depth
        elif VIEWS_CLASS in classes and self._views_depth is None:
            self._views_depth = depth
        elif DATE_CLASS in classes and self._date_depth is None:
            self._date_depth = depth
        elif tag == "time":
            self._record_time(_timestamp(_attribute(attrs, "datetime")))

    def _record_time(self, stamp: datetime | None) -> None:
        """The permalink's own timestamp wins; any other time in the post is the fallback."""
        if stamp is None:
            return
        if self._date_depth is not None:
            self._dated = self._dated or stamp
        elif self._published is None:
            self._published = stamp

    def _begin_message(self, key: str, depth: int) -> None:
        if self.messages_seen >= MAX_MESSAGES:
            raise TelegramMarkupError("Channel preview page holds more posts than expected")
        self._message_depth = depth
        self.messages_seen += 1
        self._captured = 0
        self._key = key.strip()[: MAX_CHANNEL_CHARS + 24]
        self._parts, self._views = [], []
        self._published = self._dated = None
        self._text_depth = self._views_depth = self._date_depth = None

    def _close(self, depth: int) -> None:
        if self._text_depth is not None and depth <= self._text_depth:
            self._text_depth = None
        if self._views_depth is not None and depth <= self._views_depth:
            self._views_depth = None
        if self._date_depth is not None and depth <= self._date_depth:
            self._date_depth = None
        if self._message_depth is not None and depth <= self._message_depth:
            self._finish_message()

    def _finish_message(self) -> None:
        key, parts, views = self._key, self._parts, self._views
        published = self._dated or self._published
        self._message_depth = self._text_depth = self._views_depth = self._date_depth = None
        self._key, self._parts, self._views = "", [], []
        self._published = self._dated = None
        channel, _, number = key.partition("/")
        text = _collapse(parts, MAX_EXCERPT_CHARS)
        if channel.casefold() != self._channel or not number.isdigit() or not text:
            return
        self.posts.append(
            TelegramPost(
                key=f"{channel}/{number}",
                number=int(number),
                text=text,
                published_at=published,
                views=_collapse(views, MAX_VIEW_CHARS) or None,
            )
        )


def parse_channel_preview(document: str, channel: str) -> TelegramPreview:
    """Plain-text posts from one channel preview page, or a refusal naming what failed.

    ``TelegramMarkupError`` covers every "this is not a readable preview" case: a page
    that is too large, a channel page without a message history (removed, private, a
    group, or previews switched off), and a history whose posts this parser cannot read
    (a markup change). Callers turn it into an operator-facing unavailability reason.
    """
    if len(document) > MAX_DOCUMENT_CHARS:
        raise TelegramMarkupError("Channel preview page is larger than this parser accepts")
    parser = _PreviewParser(channel)
    try:
        parser.feed(document)
        parser.close()
    except TelegramMarkupError:
        raise
    except Exception as exc:  # pragma: no cover - html.parser is lenient by design
        raise TelegramMarkupError("Channel preview page could not be parsed") from exc
    if not parser.history_seen:
        raise TelegramMarkupError(
            "The page carries no public channel history; the channel is private, removed, "
            "not a channel, or its web preview is switched off"
        )
    if not parser.posts and parser.messages_seen:
        raise TelegramMarkupError(
            "The channel history carried posts, but none belonged to this channel or held "
            "readable text; the preview markup has probably changed"
        )
    if not parser.posts:
        raise TelegramMarkupError(
            "The channel history contained no readable post; the preview markup has "
            "probably changed"
        )
    return TelegramPreview(channel, parser.title, tuple(parser.posts))
