"""Dated register assertions, not inferred ownership or verified person matches.

https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/reference/officers/list
https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/reference/persons-with-significant-control/list
"""

import json
import re
from dataclasses import replace
from typing import Any
from urllib.parse import urlencode

from ase.adapters.research_records.companies_house import PUBLIC_ORIGIN, company_number
from ase.adapters.research_records.companies_house_client import ORIGIN, CompaniesHouseClient
from ase.adapters.research_records.record_metadata import bounded_json
from ase.adapters.research_records.records import MAX_RESULTS, receipt, record_event, text
from ase.adapters.research_records.registry_lookup import RegistryLookupCapability
from ase.application.ports import Clock
from ase.domain.events import Category, Event, Reliability, content_hash
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery

LIMITATIONS = (
    "Current register context, not a historical reconstruction for the requested dates. "
    "One page, at most 20 records; further pages, PSC statements and documents were not fetched. "
    "Dates and roles are registry-reported assertions. Appointment dates can be notification dates "
    "for managing officers. Names are not verified cross-source person matches; "
    "Shared names or addresses never establish ownership. "
    "Missing records do not prove absence of control."
)


def explicit_company_number(subject: str | None) -> str | None:
    value = (subject or "").strip()
    for prefix in ("gb:", "companies-house:"):
        if value.lower().startswith(prefix):
            return company_number(value[len(prefix) :])
    return None


class CompaniesHouseOfficersProvider(RegistryLookupCapability):
    registry_namespaces = ("gb_company_number",)
    id = "research-companies-house-officers"
    name = "Companies House officers"
    endpoint = "officers"
    temporal_scope = "Current register context, not historical-window evidence or complete history."

    def __init__(self, client: CompaniesHouseClient, clock: Clock) -> None:
        self._client, self._clock = client, clock

    def supports(self, query: ResearchQuery) -> bool:
        return (
            query.focus is ResearchFocus.COMPANY
            and (not query.country_isos or "GB" in query.country_isos)
            and explicit_company_number(query.subject) is not None
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        identity = explicit_company_number(query.subject)
        if not self.supports(query) or identity is None:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Supply an explicit GB: or companies-house: company number; "
                "no name resolution was made.",
            )
        path = f"/company/{identity}/{self.endpoint}"
        url = (
            ORIGIN
            + path
            + "?"
            + urlencode(
                {
                    "items_per_page": MAX_RESULTS,
                    "start_index": 0,
                    "register_view": "false",
                }
            )
        )
        return await self._client.collect(
            self.id,
            self.name,
            url,
            lambda payload: self._parse(payload, identity, path),
            LIMITATIONS,
        )

    def _parse(self, payload: Any, identity: str, path: str) -> list[Event]:
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise ValueError("Invalid register list")
        links = payload.get("links")
        if not isinstance(links, dict) or links.get("self") != path:
            raise ValueError("Mismatched company list")
        events: list[Event] = []
        seen: set[str] = set()
        for row in payload["items"][:MAX_RESULTS]:
            if not isinstance(row, dict) or not (name := text(row.get("name"), 200)):
                continue
            fields = (
                ("appointed_on", "appointed_before", "resigned_on")
                if self.endpoint == "officers"
                else (
                    "notified_on",
                    "ceased_on",
                )
            )
            dates = {field: text(row.get(field), 40) for field in fields}
            role = text(row.get("officer_role" if self.endpoint == "officers" else "kind"), 100)
            controls = row.get("natures_of_control", [])
            controls = (
                [text(value, 120) for value in controls[:20] if isinstance(value, str)]
                if isinstance(controls, list)
                else []
            )
            controls_json, controls_omitted = bounded_json(controls)
            row_links = row.get("links")
            link = row_links.get("self") if isinstance(row_links, dict) else None
            # Links identify a filed record only and are never followed. Reject
            # arbitrary origins, traversal and cross-company record references.
            valid_link = isinstance(link, str) and bool(
                re.fullmatch(
                    rf"/company/{identity}/(?:appointments|persons-with-significant-control)/[A-Za-z0-9_/-]+",
                    link,
                )
            )
            key = (
                str(link)
                if valid_link
                else content_hash(name, role + json.dumps(dates, sort_keys=True))
            )
            if key in seen:
                continue
            seen.add(key)
            event = record_event(
                self.id,
                f"{identity}:{key}",
                f"Reported {self.endpoint}: {name}",
                f"Companies House company {identity} reports {name}, "
                f"role/type {role or 'unspecified'}. "
                f"Reported dates: {json.dumps(dates, ensure_ascii=False)}. "
                f"Reported control categories: {', '.join(controls) or 'not supplied'}. "
                "This record does not verify the intended person's identity "
                "or establish ownership from a name or address.",
                PUBLIC_ORIGIN + (str(link) if valid_link else path),
                self._clock.now(),
                category=Category.ECONOMIC,
                attributes={
                    "company_number": identity,
                    "reported_name": name,
                    "reported_role": role,
                    "reported_dates": json.dumps(dates, ensure_ascii=False),
                    "reported_natures_of_control": controls_json,
                    "reported_natures_of_control_omitted": controls_omitted,
                    "record_etag": text(row.get("etag"), 100),
                    "record_kind": "current_registry_relationship_assertion",
                    "record_issuer": "Companies House",
                    "identity_match": "requested_company_number_only",
                    "timestamp_basis": "collection time; reported dates retained separately",
                },
            )
            events.append(
                replace(
                    event,
                    reliability=Reliability.F,
                    grade_rationale="Filed relationship assertions remain unassessed.",
                )
            )
        return events


class CompaniesHousePscProvider(CompaniesHouseOfficersProvider):
    id = "research-companies-house-psc"
    name = "Companies House persons with significant control"
    endpoint = "persons-with-significant-control"
