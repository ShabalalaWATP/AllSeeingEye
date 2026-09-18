"""HTML named entities inside feeds that claim to be XML.

XML knows five entities. Publishers still write ``&mdash;`` or ``&nbsp;`` into RSS, and a
strict parser rejects the whole feed for one dash. Rewriting the HTML names as numeric
references keeps the text exactly and lets the feed parse; an unknown name is kept as its
literal text rather than left to break the parse.
"""

import re
from html.entities import name2codepoint

_XML_ENTITIES = frozenset({"amp", "lt", "gt", "quot", "apos"})
_NAMED = re.compile(r"&([A-Za-z][A-Za-z0-9]{1,31});")


def numeric_entities(text: str) -> str:
    def swap(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in _XML_ENTITIES:
            return match.group(0)
        code = name2codepoint.get(name)
        return f"&#{code};" if code is not None else f"&amp;{name};"

    return _NAMED.sub(swap, text)
