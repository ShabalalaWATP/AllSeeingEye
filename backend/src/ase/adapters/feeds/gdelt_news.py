"""Geographically coded public reporting, separate from the conflict signal feed."""

from datetime import datetime, timedelta

from ase.adapters.feeds.gdelt_events import GdeltEventsConnector
from ase.domain.events import Category, Event, Reliability, freeze_attributes
from ase.domain.news_time import news_index_date
from ase.domain.sources import SourceKind, SourceSpec

SPEC = SourceSpec(
    id="gdelt_news",
    name="GDELT geolocated news signals (unreviewed)",
    organisation="The GDELT Project",
    category=Category.NEWS,
    kind=SourceKind.API,
    url="https://data.gdeltproject.org/gdeltv2/lastupdate.txt",
    reliability=Reliability.F,
    poll_interval=timedelta(minutes=15),
    licence_note="Free for any use with attribution to gdeltproject.org",
    homepage="https://www.gdeltproject.org/",
    flags=frozenset({"machine_coded"}),
)

# Public CAMEO root labels. The six conflict/protest roots belong to gdelt_events.
NEWS_ROOTS = {
    "01": ("news_statement", "Public statement"),
    "02": ("news_appeal", "Appeal"),
    "03": ("news_intent", "Intent to cooperate"),
    "04": ("news_consultation", "Consultation"),
    "05": ("news_diplomacy", "Diplomatic cooperation"),
    "06": ("news_cooperation", "Material cooperation"),
    "07": ("news_aid", "Aid"),
    "08": ("news_yield", "Yielding"),
    "09": ("news_investigation", "Investigation"),
    "10": ("news_demand", "Demand"),
    "11": ("news_disapproval", "Disapproval"),
    "12": ("news_rejection", "Rejection"),
    "13": ("news_threat", "Threat"),
    "16": ("news_relations", "Reduced relations"),
}


class GdeltNewsConnector(GdeltEventsConnector):
    """Reuse bounded ZIP parsing and endpoint restrictions; store IDs deduplicate polls."""

    spec = SPEC
    root_codes = NEWS_ROOTS
    # Administrative connection tests share this connector. Do not consume an
    # export during a probe; normal store IDs/hashes already de-duplicate polls.
    skip_unchanged = False

    def _to_event(self, row: list[str], now: datetime) -> Event | None:
        event = super()._to_event(row, now)
        if event is None or event.url is None:
            return None
        return event.with_changes(
            title=f"News signal: {event.title}",
            # The supplied timestamp is indexing time, never an invented publication date.
            published_at=None,
            source_dates=(news_index_date(row[59]),),
            severity=None,
            attributes=freeze_attributes(
                {
                    **event.attributes,
                    "original_source_name": SPEC.name,
                    "original_source_organisation": SPEC.organisation,
                    "date_basis": "GDELT indexing time; publisher publication time unknown",
                    "geography_basis": "GDELT-coded action geography; location unverified",
                    "content_scope": "Machine-coded news signal, not the publisher headline",
                }
            ),
        )
