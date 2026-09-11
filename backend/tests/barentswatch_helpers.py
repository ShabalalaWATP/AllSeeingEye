"""Synthetic BarentsWatch records and transports, never live account credentials."""

from datetime import timedelta

import httpx
from pydantic import SecretStr

from ase.adapters.feeds import barentswatch, barentswatch_http, barentswatch_tokens
from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.barentswatch_http import BarentsWatchHttpClient
from feeds_helpers import NOW

CLIENT_ID = SecretStr("synthetic-client&name")
CLIENT_SECRET = SecretStr("synthetic-client-secret+test")
ACCESS_TOKEN = "synthetic-access-token"


def vessel(*, age=0, **overrides):
    return {
        "courseOverGround": 63.8,
        "latitude": 59.141722,
        "longitude": 5.819193,
        "name": "TEST VESSEL",
        "rateOfTurn": None,
        "shipType": 53,
        "speedOverGround": 0.1,
        "trueHeading": None,
        "mmsi": 257789800,
        "msgtime": (NOW - timedelta(seconds=age)).isoformat(),
        **overrides,
    }


def token(**overrides):
    return {
        "access_token": ACCESS_TOKEN,
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "ais",
        **overrides,
    }


def transport(monkeypatch, handler):
    async def guard(url):
        assert url in (barentswatch_http.TOKEN_URL, barentswatch_http.LATEST_URL)
        return "8.8.8.8"

    monkeypatch.setattr(barentswatch_http, "assert_public_host", guard)
    monkeypatch.setattr(feed_http, "assert_public_host", guard)
    return BarentsWatchHttpClient(
        "synthetic-tests", client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )


def monotonic_clock(monkeypatch):
    current = [1000.0]
    monkeypatch.setattr(barentswatch, "monotonic", lambda: current[0])
    monkeypatch.setattr(barentswatch_tokens, "monotonic", lambda: current[0])
    return current
