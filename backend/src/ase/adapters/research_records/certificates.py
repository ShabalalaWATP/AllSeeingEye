"""Exact-hostname certificate-transparency snapshots through a configured SSLMate account.

Official API: https://sslmate.com/help/reference/ct_search_api_v1
Free authenticated allowance: https://sslmate.com/pricing/ct_search_api
No target connection, wildcard search, pagination, certificate download or trust validation.
"""

import asyncio
import re
from collections import deque
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedCredential, FeedHttpClient
from ase.adapters.research_records.records import (
    MAX_RESULTS,
    domain_name,
    receipt,
    record_event,
    text,
)
from ase.application.ports import Clock
from ase.application.ports.research_capabilities import ProviderCapabilities
from ase.domain.events import Category, Event, Reliability
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery

ORIGIN = "https://api.certspotter.com"
ALLOWANCES = ((timedelta(seconds=1), 5), (timedelta(minutes=1), 75), (timedelta(hours=1), 100))
MAX_ROWS = 200
MAX_DNS_NAMES = 1000
LIMITATIONS = (
    "First page of unexpired issuances for one exact hostname, oldest discovery first; "
    "not the newest results, full certificate history or coverage of the requested dates. "
    "At most 20 matching records from the first 200 rows; wildcard and subdomain searches are off. "
    "Validity dates are certificate claims, not publication or observation timestamps. "
    "Log inclusion does not establish ownership, authorisation, trust or an active service. "
    "No certificates, target hosts, revocation services or later pages were fetched. "
    "The configured free account's limits can be reduced by the provider."
)


def _digest(value: Any) -> str | None:
    if not isinstance(value, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", value):
        return None
    return value.lower()


def _date(value: Any) -> datetime | None:
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.utcoffset() is not None else None
    except ValueError:
        return None


class CertificateTransparencyProvider:
    temporal_scope = (
        "First page of currently unexpired certificate issuances; no complete issuance history "
        "or latest-record guarantee. Certificate validity dates are not observation times."
    )
    id = "research-certificate-transparency"
    name = "SSLMate certificate-transparency records"

    def __init__(self, http: FeedHttpClient, clock: Clock, api_key: str | None = None) -> None:
        self._http, self._clock = http, clock
        self._requests: deque[datetime] = deque()
        self._credential: FeedCredential | None = None
        if api_key:
            if len(api_key) > 512 or any(ord(char) < 33 or ord(char) > 126 for char in api_key):
                raise ValueError("Invalid certificate-search API key configuration.")
            self._credential = FeedCredential(ORIGIN, f"Bearer {api_key}")

    def supports(self, query: ResearchQuery) -> bool:
        return query.focus is ResearchFocus.DOMAIN and domain_name(query.subject) is not None

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        domain = domain_name(query.subject)
        if not self.supports(query) or domain is None:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Supply one explicit public hostname, without a URL, IP or wildcard.",
            )
        if self._credential is None:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNAVAILABLE,
                "A free SSLMate account API key must be configured; no request was made.",
            )
        now = self._clock.now()
        while self._requests and self._requests[0] <= now - timedelta(hours=1):
            self._requests.popleft()
        if any(
            sum(at > now - window for at in self._requests) >= count for window, count in ALLOWANCES
        ):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.BUDGET_EXHAUSTED,
                "The local certificate-search allowance is exhausted; no request was made.",
            )
        url = f"{ORIGIN}/v1/issuances?" + urlencode(
            [
                ("domain", domain),
                ("include_subdomains", "false"),
                ("match_wildcards", "false"),
                ("expand", "dns_names"),
                ("expand", "issuer"),
            ]
        )
        self._requests.append(now)
        try:
            async with asyncio.timeout(15):
                payload = await self._http.get_json(
                    url,
                    conditional=False,
                    max_redirects=0,
                    credential=self._credential,
                )
            items = self._parse(payload, domain, url)
        except TimeoutError:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.TIMED_OUT,
                "Certificate search timed out; no retry was made.",
            )
        except Exception:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.FAILED,
                "Certificate search returned no usable response; no retry was made.",
            )
        return receipt(
            self.id,
            self.name,
            CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY,
            LIMITATIONS,
            items,
        )

    def _parse(self, payload: Any, domain: str, url: str) -> list[Event]:
        if not isinstance(payload, list):
            raise ValueError("Invalid issuance response")
        observed = self._clock.now()
        events: list[Event] = []
        seen: set[str] = set()
        for row in payload[:MAX_ROWS]:
            if not isinstance(row, dict):
                continue
            digest, certificate = _digest(row.get("tbs_sha256")), _digest(row.get("cert_sha256"))
            identifier = row.get("id")
            before, after = _date(row.get("not_before")), _date(row.get("not_after"))
            names = row.get("dns_names")
            if (
                not digest
                or not certificate
                or digest in seen
                or not isinstance(identifier, str)
                or not identifier
                or len(identifier) > 120
                or any(ord(char) < 32 for char in identifier)
                or before is None
                or after is None
                or before >= after
                or after <= observed
                or not isinstance(names, list)
                or len(names) > MAX_DNS_NAMES
            ):
                continue
            if not any(domain_name(name) == domain for name in names):
                continue
            issuer = row.get("issuer")
            issuer_name = text(issuer.get("friendly_name"), 200) if isinstance(issuer, dict) else ""
            issuer_name = issuer_name or "unknown"
            revoked = row.get("revoked") if type(row.get("revoked")) is bool else None
            seen.add(digest)
            event = record_event(
                self.id,
                digest,
                f"Certificate-transparency record for {domain}",
                f"SSLMate reports an issuance naming {domain}, with reported issuer {issuer_name}. "
                f"Certificate validity fields are {before.isoformat()} to {after.isoformat()}. "
                "These dates can be predated or postdated; they are not log discovery times. "
                "This record does not prove ownership, authorisation, trust or an active service.",
                url,
                observed,
                category=Category.CYBER,
                attributes={
                    "domain": domain,
                    "issuance_id": identifier,
                    "cert_sha256": certificate,
                    "tbs_sha256": digest,
                    "certificate_not_before": before.isoformat(),
                    "certificate_not_after": after.isoformat(),
                    "reported_issuer": issuer_name,
                    "reported_revoked": revoked,
                    "certificate_dns_name_count": len(names),
                    "name_match": "exact_dns_name",
                    "record_kind": "current_certificate_snapshot",
                    "record_issuer": "SSLMate CT index",
                    "timestamp_basis": "collection time; log discovery time unknown",
                    "ownership": "not established",
                    "active_service": "not checked",
                },
            )
            events.append(
                replace(
                    event,
                    reliability=Reliability.F,
                    grade_rationale="Indexed certificate record; trust and assertions unassessed.",
                )
            )
            if len(events) >= MAX_RESULTS:
                break
        return events

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            temporal_scope=self.temporal_scope,
        )
