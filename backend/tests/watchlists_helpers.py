"""Small configuration and RSS fixtures shared by watchlist tests."""

from uuid import uuid4

from ase.domain.collection import CollectionPlan, Pir, Sir
from feeds_helpers import NOW

RSS = """<rss><channel><item><guid>stable-story</guid><title>Weather report</title>
<link>https://news.google.com/rss/articles/opaque</link>
<description>&lt;p&gt;A plain-text summary&lt;/p&gt;</description>
<pubDate>Sat, 05 Sep 2026 00:00:00 GMT</pubDate></item></channel></rss>"""


def plan(*terms: str, enabled: bool = True) -> CollectionPlan:
    return CollectionPlan(
        id=uuid4(),
        name="Watch",
        description="",
        aoi_id=None,
        countries=(),
        pirs=(Pir("PIR-1", "Question", (Sir("SIR-1.1", "Detail", terms),)),),
        enabled=enabled,
        created_by=uuid4(),
        created_at=NOW,
        updated_at=NOW,
    )


class MutablePlans:
    def __init__(self, plans: list[CollectionPlan]) -> None:
        self.plans = plans
        self.reads = 0

    async def enabled_plans(self) -> list[CollectionPlan]:
        self.reads += 1
        return self.plans
