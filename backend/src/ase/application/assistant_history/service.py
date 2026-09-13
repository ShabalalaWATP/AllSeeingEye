"""Framework-free limits for private user-controlled chat snapshots."""

import json
from collections.abc import Sequence

from ase.domain.errors import InvalidRequest

MAX_TRANSCRIPT_BYTES = 65_536
MAX_SAVED_CONVERSATIONS = 30


def encode_transcript(turns: Sequence[dict[str, object]]) -> tuple[str, int]:
    text = json.dumps({"turns": list(turns)}, ensure_ascii=False, separators=(",", ":"))
    size = len(text.encode("utf-8"))
    if size > MAX_TRANSCRIPT_BYTES:
        raise InvalidRequest("Saved conversation exceeds the 64 KB limit.")
    return text, size


def require_capacity(count: int) -> None:
    if count >= MAX_SAVED_CONVERSATIONS:
        raise InvalidRequest("You can save up to 30 Ask Eye conversations.")
