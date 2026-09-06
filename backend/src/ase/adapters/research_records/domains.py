"""Current DNS and .com/.net registry snapshots, never ownership attribution.

Official contracts: https://developers.google.com/speed/public-dns/docs/doh/json
https://www.verisign.com/news-insights/registration-data-access-protocol/help/
No target-host connection, registrar referral, pagination or secondary DNS lookup is made.
"""

import ipaddress
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.research_records.records import (
    collect_json,
    domain_name,
    receipt,
    record_event,
    text,
)
from ase.application.ports import Clock
from ase.domain.events import Category, Event
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery

DNS_TYPES = {"A": 1, "AAAA": 28, "MX": 15, "NS": 2}


def _answer_value(value: Any, record_type: str) -> str:
    if not isinstance(value, str) or len(value) > 300:
        return ""
    if record_type in {"A", "AAAA"}:
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            return ""
        expected = 4 if record_type == "A" else 6
        return str(address) if address.version == expected else ""
    if record_type == "NS":
        return domain_name(value) or ""
    parts = value.split()
    if len(parts) == 2 and parts[0].isdigit() and 0 <= int(parts[0]) <= 65535:
        # RFC7505 null MX explicitly means no mail service; '.' is not an owner name.
        target = "." if parts[0] == "0" and parts[1] == "." else domain_name(parts[1])
        if target:
            return f"{int(parts[0])} {target}"
    return ""


class DnsResearchProvider:
    """One configured RR type per admitted call; ANY is deliberately unsupported."""

    def __init__(self, http: FeedHttpClient, clock: Clock, record_type: str = "A") -> None:
        if record_type not in DNS_TYPES:
            raise ValueError("Supported DNS types are A, AAAA, MX and NS")
        self._http, self._clock, self._type = http, clock, record_type

    @property
    def id(self) -> str:
        return f"research-dns-{self._type.lower()}"

    @property
    def name(self) -> str:
        return f"Google Public DNS {self._type} records"

    def supports(self, query: ResearchQuery) -> bool:
        return query.focus is ResearchFocus.DOMAIN and domain_name(query.subject) is not None

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        domain = domain_name(query.subject)
        if not self.supports(query) or domain is None:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Supply an explicit public domain name, without a URL, address or credentials.",
            )
        url = "https://dns.google/resolve?" + urlencode(
            {
                "name": domain,
                "type": self._type,
                "cd": "false",
                "edns_client_subnet": "0.0.0.0/0",
            }
        )
        return await collect_json(
            self._http,
            self.id,
            self.name,
            url,
            lambda data: self._parse(data, domain, url),
            "Current resolver snapshot, not historical DNS. Shared addresses, mail servers "
            "or nameservers do not establish common ownership. No target host was contacted.",
        )

    def _parse(self, data: dict[str, Any], domain: str, url: str) -> list[Event]:
        if type(data.get("Status")) is not int or data["Status"] not in {0, 3}:
            raise ValueError("DNS response failed")
        if data.get("TC") is True:
            raise ValueError("Truncated DNS response")
        question = data.get("Question")
        if not isinstance(question, list) or not any(
            isinstance(q, dict)
            and domain_name(q.get("name")) == domain
            and q.get("type") == DNS_TYPES[self._type]
            for q in question[:8]
        ):
            raise ValueError("Mismatched DNS question")
        if data["Status"] == 3:
            return []
        answers = data.get("Answer", [])
        if not isinstance(answers, list):
            raise ValueError("Invalid DNS answer")
        records = [item for item in answers[:100] if isinstance(item, dict)]
        reachable = {domain}
        for _ in range(8):
            for answer in records:
                if answer.get("type") == 5 and domain_name(answer.get("name")) in reachable:
                    target = domain_name(answer.get("data"))
                    if target:
                        reachable.add(target)
        values = sorted(
            {
                value
                for answer in records
                if answer.get("type") == DNS_TYPES[self._type]
                and domain_name(answer.get("name")) in reachable
                and (value := _answer_value(answer.get("data"), self._type))
            }
        )[:20]
        if not values:
            return []
        answer_text = "; ".join(values)[:1200]
        return [
            record_event(
                self.id,
                f"{domain}:{self._type}",
                f"DNS {self._type} snapshot: {domain}",
                f"Google Public DNS returned {answer_text}. Current resolver observation "
                "only; shared infrastructure does not identify the owner or prove a "
                "relationship. DNSSEC status is the resolver's assertion, not independent "
                "client verification.",
                url,
                self._clock.now(),
                category=Category.CYBER,
                attributes={
                    "domain": domain,
                    "record_type": self._type,
                    "answer_count": len(values),
                    "resolver_dnssec_authenticated": data.get("AD") is True,
                    "record_kind": "current_dns_snapshot",
                },
            )
        ]


class RdapResearchProvider:
    id = "research-rdap"
    name = "Verisign domain registry RDAP"

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http, self._clock = http, clock

    def supports(self, query: ResearchQuery) -> bool:
        domain = domain_name(query.subject)
        # Avoid guessing a registrable name from a hostname or unknown suffix.
        return query.focus is ResearchFocus.DOMAIN and bool(
            domain and domain.count(".") == 1 and domain.rsplit(".", 1)[1] in {"com", "net"}
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        domain = domain_name(query.subject)
        if not self.supports(query) or domain is None:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "This bounded RDAP provider supports explicit registered .com and .net "
                "domains only; no registrable-domain inference or referral lookup is made.",
            )
        suffix = domain.rsplit(".", 1)[1]
        url = f"https://rdap.verisign.com/{suffix}/v1/domain/{domain}"
        return await collect_json(
            self._http,
            self.id,
            self.name,
            url,
            lambda data: self._parse(data, domain, url),
            "Current registry snapshot only, not historical ownership. Registrar referrals "
            "and contact records were not fetched; redaction or missing registrant "
            "information is not evidence of concealment.",
        )

    def _parse(self, data: dict[str, Any], domain: str, url: str) -> list[Event]:
        if data.get("errorCode") == 404:
            return []
        if data.get("objectClassName") != "domain" or domain_name(data.get("ldhName")) != domain:
            raise ValueError("Mismatched RDAP domain")
        statuses = data.get("status", [])
        nameservers = data.get("nameservers", [])
        events = data.get("events", [])
        if not all(isinstance(value, list) for value in (statuses, nameservers, events)):
            raise ValueError("Invalid RDAP fields")
        state = ", ".join(text(item, 80) for item in statuses[:8] if isinstance(item, str))
        servers = ", ".join(
            name
            for server in nameservers[:10]
            if isinstance(server, dict) and (name := domain_name(server.get("ldhName")))
        )
        dates = "; ".join(
            f"{text(event.get('eventAction'), 50)}: {text(event.get('eventDate'), 40)}"
            for event in events[:10]
            if isinstance(event, dict)
        )
        return [
            record_event(
                self.id,
                domain,
                f"Registry snapshot: {domain}",
                f"Registry status: {state or 'not supplied'}. "
                f"Nameservers: {servers or 'not supplied'}. "
                f"Registry event dates: {dates or 'not supplied'}. Current registration "
                "metadata does not establish beneficial ownership, attribution or "
                "historical control.",
                url,
                self._clock.now(),
                category=Category.CYBER,
                attributes={
                    "domain": domain,
                    "registry_handle": text(data.get("handle"), 200),
                    "record_kind": "current_registry_snapshot",
                },
            )
        ]
