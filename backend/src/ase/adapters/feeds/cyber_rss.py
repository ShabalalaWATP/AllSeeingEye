"""Keep CTI publications separate from located incidents in live and private collection."""

from dataclasses import replace
from datetime import datetime

# Types only: XML parsing remains in the shared defusedxml RSS pipeline.
# nosemgrep: python.lang.security.use-defused-xml.use-defused-xml
from xml.etree.ElementTree import Element  # nosec B405

from ase.adapters.feeds.rss import RssConnector
from ase.domain.events import Event, GeoConfidence, freeze_attributes
from ase.domain.source_dates import SourceDate, resolve_source_date
from ase.domain.sources import SourceSpec


def cyber_publication(event: Event, spec: SourceSpec) -> Event:
    """Publisher metadata cannot establish affected geography or corroboration."""
    dates = tuple(
        _cert_eu_date(row) if spec.id == "cyber_cert_eu" else row for row in event.source_dates
    )
    published = next((row.value for row in dates if row.role == "publication"), event.published_at)
    return event.with_changes(
        published_at=published,
        source_dates=dates,
        point=None,
        country_iso=None,
        geometry=None,
        geo_confidence=GeoConfidence.NONE,
        attributes=freeze_attributes(
            {
                **event.attributes,
                "original_source_id": spec.id,
                "original_source_name": spec.name,
                "original_source_organisation": spec.organisation,
                "original_publisher": spec.name,
                "content_scope": "publisher headline and attribution metadata only",
                "geography_basis": "Incident geography unknown; publisher location is not evidence",
                "attribution_status": "Publisher assertions, not independently verified",
            }
        ),
    )


class CyberRssConnector(RssConnector):
    def _to_event(self, item: Element, now: datetime) -> Event | None:
        event = super()._to_event(item, now)
        return cyber_publication(event, self.spec) if event is not None else None


def _cert_eu_date(row: SourceDate) -> SourceDate:
    """CERT-EU declares Central European standard/summer time in its RSS pubDate."""
    if row.field != "pubDate" or row.value is not None:
        return row
    text = row.raw_text.strip()
    for zone, offset in ((" CEST", " +0200"), (" CET", " +0100")):
        if text.endswith(zone):
            resolved = resolve_source_date(
                text[: -len(zone)] + offset,
                row.field,
                "gregorian",
                basis="source_spec",
            )
            return replace(
                resolved,
                raw_text=row.raw_text,
                method="ase-cert-eu-pubdate-zone-v1",
                limitations=("CERT-EU explicit CET/CEST suffix converted to +0100/+0200.",),
            )
    return row
