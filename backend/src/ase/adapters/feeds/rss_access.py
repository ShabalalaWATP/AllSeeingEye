"""Publisher feeds that refuse identified automated clients: wait and explain, never evade.

Both refusals were observed on 15 September 2026 with the application's own user agent.
The same requests succeed for browsers or for other TLS clients, so the refusal is the
publisher's bot protection, not a fault this client can correct. The application does
not imitate a browser or another client. It retries at a slow cadence and tells the
operator why the source is idle, instead of spending the circuit breaker on it.
"""

from collections.abc import Mapping
from datetime import timedelta
from types import MappingProxyType

from ase.adapters.feeds.http_contracts import FeedFetchError, FeedHttpStatusError

REFUSAL_RECHECK = timedelta(hours=12)
AUTOMATION_REFUSALS: Mapping[str, str] = MappingProxyType(
    {
        "cyber_cisa_advisories": (
            "CISA's advisory RSS refuses this application's HTTP client (CDN HTTP 403 since "
            "15 September 2026) while serving browsers. The application will not imitate a "
            "browser; it rechecks every 12 hours. CISA KEV is collected separately; "
            "ICS advisories are also published as CSAF in cisagov/CSAF."
        ),
        "news_cbc_canada": (
            "CBC's feed servers hold this application's requests open without answering "
            "(observed on 18 September 2026 on every CBC feed address, while a browser user "
            "agent is answered at once). The application will not imitate a browser; it "
            "rechecks every 12 hours."
        ),
        "cyber_acsc_advisories": (
            "cyber.gov.au holds automated connections open without answering (observed site "
            "wide on 15 September 2026, including its RSS feeds). No other official ACSC feed "
            "address was found. The application will not imitate a browser; it rechecks "
            "every 12 hours."
        ),
    }
)


def automation_refusal(source_id: str, error: FeedFetchError) -> str | None:
    """The operator-facing reason when a known refusing publisher fails in its known way."""
    reason = AUTOMATION_REFUSALS.get(source_id)
    if reason is None:
        return None
    if isinstance(error, FeedHttpStatusError) and error.status_code not in (401, 403):
        return None
    return reason
