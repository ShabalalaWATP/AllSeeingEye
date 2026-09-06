"""The supported native Bedrock credential destination, independent of HTTP clients."""

import re

from ase.domain.llm import normalise_base_url

_RUNTIME_ROOT = re.compile(
    r"https://bedrock-runtime\.[a-z]{2}(?:-[a-z]+){1,2}-[0-9]+\.amazonaws\.com"
)


def normalise_bedrock_base_url(value: str) -> str:
    """Accept only a canonical regional runtime root, with an optional trailing slash."""
    candidate = normalise_base_url(value)
    if not _RUNTIME_ROOT.fullmatch(candidate):
        raise ValueError("Use a canonical HTTPS regional Bedrock runtime root address.")
    return candidate
