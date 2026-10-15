"""Attribute-only DTDs are rejected before native XML declaration processing."""

from collections.abc import Callable

import pytest
from defusedxml.common import DTDForbidden

from ase.adapters.feeds.cyclones import _parse_xml
from ase.adapters.feeds.gdacs import GdacsConnector
from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.rss import RssConnector
from ase.adapters.feeds.tsunami import TsunamiConnector
from ase.adapters.feeds.volcanoes import VolcanoReportConnector
from ase.adapters.geo.camera_east import parse_estonia
from ase.adapters.geo.camera_europe_maps import parse_luxembourg
from ase.adapters.geo.camera_world import parse_newzealand
from ase.adapters.geo.cameras import parse_hongkong
from ase.adapters.research.feed import ResearchFeedParser
from feeds_helpers import NOW, FakeClock, FakeHttp, make_spec
from research_feed_helpers import QUERY

DTD = '<!DOCTYPE rss [<!ATTLIST rss mode CDATA "private-marker">]><rss><channel/></rss>'


@pytest.mark.parametrize("kind", ["rss", "gdacs", "tsunami", "volcanoes"])
async def test_feed_dtd_rejection_uses_existing_sanitised_error(kind: str) -> None:
    http, clock = FakeHttp({"": DTD}), FakeClock(NOW)
    connectors = {
        "rss": RssConnector(http, clock, make_spec()),  # type: ignore[arg-type]
        "gdacs": GdacsConnector(http, clock),  # type: ignore[arg-type]
        "tsunami": TsunamiConnector(http, clock),  # type: ignore[arg-type]
        "volcanoes": VolcanoReportConnector(http, clock),  # type: ignore[arg-type]
    }
    with pytest.raises(FeedFetchError) as error:
        await connectors[kind].fetch()
    assert "private-marker" not in str(error.value)


def test_cyclone_dtd_rejection_uses_existing_error() -> None:
    with pytest.raises(FeedFetchError):
        _parse_xml(DTD, "synthetic")


def test_research_feed_rejects_dtd_before_mapping() -> None:
    parser = ResearchFeedParser(FakeHttp(), FakeClock(NOW), make_spec())  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        parser.parse(DTD, QUERY, local_match=False)


@pytest.mark.parametrize(
    "parser", [parse_estonia, parse_luxembourg, parse_newzealand, parse_hongkong]
)
@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_camera_dtd_is_rejected_in_each_supported_xml_encoding(
    parser: Callable[[bytes], object], encoding: str
) -> None:
    with pytest.raises(ValueError) as error:
        parser(DTD.encode(encoding))
    assert isinstance(error.value, DTDForbidden) or isinstance(error.value.__cause__, DTDForbidden)
