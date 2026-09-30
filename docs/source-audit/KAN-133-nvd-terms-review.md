# KAN-133: NVD API terms and rate review

Reviewed on 30 September 2026 at 11:55 UTC against the live
[KAN-133 criterion](https://alex-orr.atlassian.net/browse/KAN-133), which requires
verified NVD public rate limits and provider licensing before release.
Implementation reviewed: `04d00368`.

## Primary evidence

The web reader returned no readable content for the official developer pages.
Two bounded, unauthenticated HTTP GETs then returned status 200 and 2,453-byte
JavaScript app shells. Rendering those same public URLs in Edge exposed the
complete policy text. This supersedes the earlier unavailable-page observation;
it is not inferred from third-party summaries or successful API responses.

| Official page | Visible evidence on the review date |
| --- | --- |
| [NVD Getting Started](https://nvd.nist.gov/developers/start-here#divRateLimits) | The Rate Limits section states five requests per rolling 30 seconds without an API key, or fifty with a key. The page shows an update date of 25 February 2025. |
| [NVD Getting Started: Best Practices](https://nvd.nist.gov/developers/start-here#divBestPractices) | Recommends six seconds between requests and one requestor for enterprise synchronisation. Its incremental repository workflow recommends polling no more often than every two hours. |
| [NVD API Terms of Use](https://nvd.nist.gov/developers/terms-of-use) | Defines API use, attribution, content modification, access limits and warranty disclaimers. No policy revision date is displayed. |

The Getting Started page describes NIST publications as public-domain material.
That statement does not replace the API-specific conditions. The terms permit
services that retrieve, display and analyse NVD data, ask for prominent attribution
without implied endorsement, and forbid attributing modified API content to NVD.
They provide no warranty of accuracy or uninterrupted access.

The Attribution section supplies this exact notice:

> This product uses the NVD API but is not endorsed or certified by the NVD.

The terms say that requestors sharing a proxy/firewall also share its rate limit.
Multiple application instances may collectively reach the limit. Keys belong to
the original requestor and must not be shared with other people or organisations.
Exceeding or circumventing access limits can result in a block. These points come
from the [Use Limitations section](https://nvd.nist.gov/developers/terms-of-use#divUseLimitations).

## Match to the implementation

`backend/src/ase/adapters/feeds/kev_scores.py` reserves its next attempt before
network work. Each enrichment instance makes at most one NVD request per
24-hour cycle, using a thirty-day KEV filter and at most 1,000 returned records.
It performs no pagination or immediate retry after a failure. Its normal request
cadence is below the verified public limit without a key.

The counter and cache are in memory. A process restart starts a fresh allowance,
and this is not a distributed quota shared with other processes or products.
Operators must coordinate those callers and repeated restarts behind a common
egress address; this review does not certify an arbitrary multi-instance topology.
The implementation's bounded partial-enrichment behaviour remains unchanged.

## Acceptance and follow-up

The published NVD terms and numeric public rate policy have now been directly
verified. At the reviewed commit, the Cyber workspace names NVD and preserves
score provenance, but it does not display the requested non-endorsement notice.
That presentation follow-up is required before considering this release review
complete. This document alone does not add the application notice.

No API key, registration, policy-acceptance form, external message, production
setting or new data request was used for this review. The earlier successful
bounded CVSS response remains the live data-shape evidence in the
[source delivery record](../delivery/KAN-130-sources-exports.md). No application
tests were rerun for this documentation-only review.
