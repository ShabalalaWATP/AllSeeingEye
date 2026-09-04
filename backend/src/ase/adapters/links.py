"""Builds the public links the SPA understands for activation and password reset."""

from __future__ import annotations

from urllib.parse import quote

from ase.domain.tokens import TokenPurpose

PATHS = {TokenPurpose.ACTIVATION: "/activate", TokenPurpose.RESET: "/reset-password"}


class PublicLinkBuilder:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def link_for(self, purpose: TokenPurpose, secret: str) -> str:
        return f"{self._base_url}{PATHS[purpose]}?token={quote(secret, safe='')}"
