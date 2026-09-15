"""Radar attack percentages remain bounded aggregates, never incident coordinates."""

from datetime import timedelta

from ase.adapters.feeds.http import FeedCredential
from ase.adapters.feeds.radar_attack_trends import RadarAttackTrends
from feeds_helpers import NOW
from helpers import FakeClock


class RadarHttp:
    def __init__(self, *, malformed_layer7: bool = False) -> None:
        self.calls: list[tuple[str, FeedCredential]] = []
        self.malformed_layer7 = malformed_layer7

    async def get_json(
        self, url: str, *, credential: FeedCredential, conditional: bool, max_redirects: int
    ) -> object:
        assert max_redirects == 0
        self.calls.append((url, credential))
        layer7 = "/layer7/" in url
        return {
            "success": True,
            "result": {
                "meta": {
                    "normalization": (
                        "RAW_VALUES" if layer7 and self.malformed_layer7 else "PERCENTAGE"
                    ),
                    "dateRange": [
                        {
                            "startTime": (NOW - timedelta(days=1)).isoformat(),
                            "endTime": NOW.isoformat(),
                        }
                    ],
                    "lastUpdated": NOW.isoformat(),
                    "units": [{"name": "*", "value": "requests" if layer7 else "bytes"}],
                },
                "top_0": [
                    {
                        "rank": 1,
                        "targetCountryAlpha2": "GB",
                        "targetCountryName": "United Kingdom",
                        "value": "42.5",
                    },
                ],
            },
        }


async def test_radar_attack_trends_cache_two_layers_and_keep_token_off_urls() -> None:
    http = RadarHttp()
    trends = RadarAttackTrends(http, FakeClock(NOW), "test-token")  # type: ignore[arg-type]
    first = await trends.read()
    second = await trends.read()
    assert first is second and first.status == "ready"
    assert len(http.calls) == 2
    assert {layer.layer for layer in first.layers} == {"layer3", "layer7"}
    assert {layer.unit for layer in first.layers} == {"bytes", "requests"}
    assert all(len(layer.countries) == 1 for layer in first.layers)
    assert all(layer.countries[0].share_percent == 42.5 for layer in first.layers)
    assert all("test-token" not in url for url, _ in http.calls)
    assert all(credential.origin == "https://api.cloudflare.com" for _, credential in http.calls)


async def test_radar_attack_trends_report_partial_and_missing_credentials() -> None:
    http = RadarHttp(malformed_layer7=True)
    partial = await RadarAttackTrends(http, FakeClock(NOW), "test-token").read()  # type: ignore[arg-type]
    assert partial.status == "partial" and [layer.layer for layer in partial.layers] == ["layer3"]
    absent = await RadarAttackTrends(http, FakeClock(NOW), None).read()  # type: ignore[arg-type]
    assert absent.status == "not_configured" and not absent.layers
    assert len(http.calls) == 2
