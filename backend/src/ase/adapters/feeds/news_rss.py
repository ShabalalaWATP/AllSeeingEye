"""Publisher headline metadata without inferred incident geography or article collection."""

from datetime import datetime

# Types only; parsing stays in the shared defusedxml connector.
# nosemgrep: python.lang.security.use-defused-xml.use-defused-xml
from xml.etree.ElementTree import Element  # nosec B405

from ase.adapters.feeds.rss import RssConnector, child_text
from ase.application.feeds.pipeline import clean_text
from ase.domain.events import Event, GeoConfidence, freeze_attributes


class NewsRssConnector(RssConnector):
    def _to_event(self, item: Element, now: datetime) -> Event | None:
        event = super()._to_event(item, now)
        if event is None:
            return None
        return event.with_changes(
            point=None,
            country_iso=None,
            geo_confidence=GeoConfidence.NONE,
            attributes=freeze_attributes(
                {
                    **event.attributes,
                    "original_source_id": self.spec.id,
                    "original_source_name": self.spec.name,
                    "original_source_organisation": self.spec.organisation,
                    "original_publisher": self.spec.name,
                    "declared_upstream_publisher": clean_text(child_text(item, "source"), 120),
                    "provenance_status": "Publisher-attributed; claims unverified",
                    "content_scope": "Publisher headline and attribution metadata only",
                    "publication_scope": self.spec.rating.scope if self.spec.rating else None,
                    "geography_basis": "Publisher coverage does not establish incident geography",
                    "research_scope": "Retained feed evidence; no fresh private publisher search",
                }
            ),
        )
