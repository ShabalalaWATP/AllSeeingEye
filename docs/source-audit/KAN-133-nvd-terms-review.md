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
verified. The initial review at `04d00368` found that the Cyber workspace named
NVD and preserved score provenance but lacked the requested non-endorsement
notice. The subsequent presentation change adds the exact Terms of Use wording
once above the vulnerability catalogue, with a link to those terms. It remains
visible when results are empty or scores are unavailable. Score and request logic
are unchanged. This completes the identified terms-verification and notice work;
the shared-egress operating constraints above still apply.

All 17 existing tests in `CyberVulnerabilities.test.tsx`, `CyberDetails.test.tsx`
and `CyberPage.test.tsx` pass. Both TypeScript configurations, changed-file ESLint,
Prettier and whitespace checks pass. A private loopback fixture preview rendered
the actual component and theme: the notice was visibly readable above sorting
and data for scored, missing-score and empty states. The preview made no provider
requests and was stopped after inspection. No new test merely repeating the
notice was added; no coverage percentage was measured for this small change.
An independent static review found no actionable issue in the exact wording,
unconditional placement, existing safe external-link handling or unchanged score
logic. It did not repeat the runtime tests or primary-source browser capture.

No API key, registration, policy-acceptance form, external message, production
setting or new data request was used for this review. The earlier successful
bounded CVSS response remains the live data-shape evidence in the
[source delivery record](../delivery/KAN-130-sources-exports.md). No application
tests were needed for the initial documentation-only commit; the checks above
cover the separate application-notice change.
