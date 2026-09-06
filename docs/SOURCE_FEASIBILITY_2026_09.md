# Regional public RSS feasibility, September 2026

Checked 6 September 2026, approximately 18:00 to 18:15 UTC, from the development
host. This is a point-in-time transport/parser check, not a reliability assessment
or proof of continuing availability. No credentials, paywall access, page-content
collection, mirrors of blocked pages or anti-bot bypasses were used.

## Enabled first slice

Eight publisher-discovered feeds have seeds in `rss_seeds_regional.py` and use the
existing guarded `FeedHttpClient` and `RssConnector`. The application smoke test
successfully parsed each feed using its normal DNS checks, pinned destination,
TLS verification, redirect limits and response-size limits. No descriptions or
article bodies were retained by these new connectors.

| ID / language | Publisher discovery and exact feed | Observed response | Application result / newest publication UTC |
| --- | --- | --- | --- |
| `meduza_ru` / Russian | [Meduza homepage](https://meduza.io/) advertises an RSS alternate at [RSS all](https://meduza.io/rss/all) | 200, `application/rss+xml`, 351,012 bytes, RSS root, 30 items | 30 events; 6 September 17:06:55 |
| `mediazona_ru` / Russian | [Mediazona footer](https://zona.media/) links to [RSS](https://zona.media/rss) | 200, `text/xml`, 21,666 bytes, RSS root, 50 items | 50 events; 6 September 17:12:28 |
| `insider_ru` / Russian | [The Insider menu](https://theins.ru/) links to [feed](https://theins.ru/feed) | 200, `application/xml`, 397,086 bytes, RSS root, 50 items | 50 events; 6 September 16:38:43 |
| `cdt_zh` / Chinese | Publisher's [subscription guidance](https://chinadigitaltimes.net/chinese/184613.html) names the all-content [FeedBurner feed](https://feeds.feedburner.com/chinadigitaltimes/IyPt) | 200, `text/xml`, 92,896 bytes, RSS root, 7 items | 7 events; 6 September 15:00:45 |
| `hrana_fa` / Persian | [HRANA homepage](https://www.hra-news.org/) explicitly links to [feed](https://www.hra-news.org/feed/) | 200, `application/rss+xml`, 43,324 bytes, RSS root, 30 items | 30 events; 6 September 18:09:22 |
| `hrana_en` / English | Same publisher homepage links to `http://hra-news.org/en/feed`; its HTTPS publisher path redirects normally to [English feed](https://www.en-hrana.org/feed/) | 200, `application/rss+xml`, 46,298 bytes, RSS root, 10 items; final URL separately checked | 10 events; 4 September 16:06:08 |
| `iranwire_fa` / Persian | [Persian homepage](https://iranwire.com/fa/) advertises [RSS alternate](https://iranwire.com/fa/feed/) | 200, `application/rss+xml`, 940,209 bytes, RSS root, 735 items | Newest 200 events; 6 September 16:55:56 |
| `iranwire_en` / English | [English homepage](https://iranwire.com/en/) advertises [RSS alternate](https://iranwire.com/en/feed/) | 200, `application/rss+xml`, 270,927 bytes, RSS root, 483 items | Newest 200 events; 4 September 16:31:37 |

Byte counts and item counts are observations of those responses, not fixed schema
guarantees. The older CDT subscription page alone was insufficient to enable its
endpoint: the linked endpoint was then fetched and parsed successfully, with
current publication dates. FeedBurner is the delivery service, not an additional
publisher or independent corroboration source.

## Attribution, collection and reuse limits

- New sources start at F6 (source reliability and claim credibility cannot yet be
  judged), with unassessed rating metadata. Political alignment and public feed
  availability confer no grade. Existing source grades were not changed.
- Meduza's two editions share the `Meduza` organisation key. HRANA's editions share
  `Human Rights Activists in Iran`; IranWire's editions share `IranWire`. Translated
  editions therefore do not introduce another organisation for corroboration.
- CDT is labelled aggregation. A story it republishes is not automatically an
  independent observation. HRANA is labelled NGO human-rights reporting. None of
  these additions is labelled a government statement or an official state source.
- Transport is unauthenticated HTTPS RSS, with no account requirement observed.
  The intentional collection scope is publisher titles, dates, attribution and
  canonical item links. Description/content fields and imagery are excluded from
  event output. Publisher-supplied RSS supports subscription discovery; broader
  article/image retention and redistribution rights have not been established.
  This is not an open-content licence declaration.
- Raw public events use the existing bounded, in-memory event store. Any subsequent
  assessment may preserve only the selected headline-level evidence through the
  existing report pipeline. Full-article reading/import needs its own supported
  access and reuse decision.
- Native text and source dates are preserved. `zh` describes the publisher's
  Chinese edition; this feed is not a separate traditional-Chinese source.
- A report's publisher location is never used as incident geometry. These feeds
  do not gain coordinates from the Russia, China or Iran collection context.
- Poll intervals are operator policy, not publisher promises: 30 minutes for the
  Russian feeds, HRANA Persian and IranWire Persian; 60 minutes for CDT, HRANA
  English and IranWire English. Existing conditional requests/backoff remain in
  use. No historical last-success value is injected into application health.

## Parser findings and bounds

IranWire's English response started with 5 August material but contained newer
4 September material later in the same feed. Taking its first 200 entries would
miss recent reporting. Both IranWire seeds therefore select the newest entries
using a heap of at most 200 item references, within the existing 5 MiB HTTP body
cap. The XML tree is bounded by that byte cap; no unbounded page traversal or
pagination was introduced.

Returned events carry `feed_items_available`, `feed_items_limit` and
`feed_items_truncated` when the upstream response exceeds the item limit. This is
a bounded recent-feed window, not a complete archive. IranWire English's observed
coverage was 5 August to 4 September; Persian covered 7 August to 6 September.
The other feeds exposed only their observed 7 to 50 current entries.

The RSS parser now rejects a well-formed HTML or error-XML root as an unavailable
feed instead of returning an empty successful result. Valid empty RSS remains a
valid empty feed. Existing RSS 2.0, RDF and Atom handling is covered by regression
tests. Parser behaviour remains date-aware, HTML-stripped where summaries are
permitted, byte-limited through the HTTP port, and limited to 200 output events.

## Not enabled and blocked checks

| Candidate | Actual observation | Decision |
| --- | --- | --- |
| CDT direct homepage/subscription page | Normal HTTP client received 403 HTML; browser research could read publisher subscription guidance | Do not scrape the blocked site; use only the publisher-documented functioning feed delivery endpoint above |
| HRANA bare-host English homepage `https://en-hrana.org/` | 403 HTML | Do not treat that homepage as operational; publisher-linked `www.en-hrana.org/feed/` independently returned valid RSS through normal HTTPS redirect discovery |
| [Iran Human Rights](https://iranhr.net/en/) | 403 HTML from normal client | No feed added, no workaround attempted |
| [Iran International](https://www.iranintl.com/en) | 200 HTML; no RSS/Atom alternate or feed link found in inspected homepage | No guessed production endpoint and no page-scraping connector |
| [Radio Farda](https://www.radiofarda.com/) | Homepage advertised `/api/`; ordinary fetch returned RSS, 20 items, newest 6 September 17:30 UTC | Discovery recorded only; not added in this slice pending publisher/funding context and reuse review |
| Government/MFA and map/dataset backlog | Not probed by this RSS slice | Remain at their previous documented feasibility status; no claim of regional completeness |

## Offline verification

Synthetic fixtures test native Russian, Chinese and Persian titles, source
language, dates and links, excluded descriptions, missing geometry, unassessed
grades, shared publisher families, stable repeated identifiers, oldest-first
truncation, valid empty feeds and HTML/error rejection. No copied publisher
articles or live network calls are part of the test suite.

Focused command: `uv run pytest tests/test_regional_rss.py tests/test_rss.py --no-cov -q`.
Result: 21 tests passed. The live smoke test above was a separate, deliberate
read-only check, not a fixture-backed assertion or a continuously monitored SLA.

## On-demand research integration

`RegionalFeedResearchProvider` exposes `research_regional_<seed ID>` for the same
eight seeds. It performs one guarded public-feed request and matches explicit
phrases locally against headlines, within the requested half-open publication-date
interval. The private question and search phrases do not go upstream. Undated
items are excluded rather than dated at retrieval time. Shared parsing honours
headline-only and newest-200 selection and preserves truncation attributes.

RU, CN and IR presets route to their relevant feeds. An explicitly selected source
can still contribute cross-region context. Feed language must be selected; CDT's
Chinese seed accepts `zh`, `zh-CN` and `zh-Hans`, without claiming a separate
traditional-Chinese edition. Persian comparison handles Arabic kaf/yeh variants
without changing the stored original text. Publisher organisation keys remain
available in the source catalogue; collection adds no new reliability assessment.

The provider reports actual configured language and a recent-snapshot temporal
scope. `FAILED` means no coverage was established; `EMPTY` means no dated headline
matched within this bounded feed window, not absence of real-world events.

Additional focused verification: regional research, regional RSS, existing RSS
and existing research feeds, 58 tests passed. Tests use only synthetic HTTP/XML
fixtures. Container/source-catalogue wiring is coordinated separately.

## E8: OONI country/day aggregates

Checked 6 September 2026, approximately 18:20 to 18:30 UTC. The
[OONI API homepage](https://api.ooni.io/) links to its
[API documentation](https://api.ooni.io/apidocs/), whose current machine-readable
schema is [apispec_1.json](https://api.ooni.io/apispec_1.json). That schema documents
`GET /api/v1/aggregation`, country filters, measurement dates, daily time grain
and aggregation dimensions. It does not require an API key. The homepage requests
a modest request rate and discourages batch consumption; no numeric quota was
asserted by this implementation.

A normal request used exactly these parameters:

```text
https://api.ooni.io/api/v1/aggregation
probe_cc=IR
test_name=web_connectivity
since=2026-09-04T00:00:00
until=2026-09-05T00:00:00
axis_x=measurement_start_day
time_grain=day
```

The response was HTTP 200, `application/json`, 298 bytes. It declared
`dimension_count: 1` and contained one daily record for 4 September: 23,117 tests,
2,924 anomalous, 6,509 upstream-confirmed, 609 failed and 13,075 OK. Counts sum to
the supplied measurement denominator. This is a point-in-time response, not a
frozen historical truth or a judgement about Iran's entire population/network.
No probe identifiers, IPs, URLs tested, ASNs or precise locations were requested.

The implemented `OoniAggregateProvider` then passed a separate smoke test through
the normal guarded HTTP client, returning one F6 country-level event with the
same counters and no map point. Its interface is explicit source selection plus
a two-letter country code, or a subject such as `ooni:IR`. It does not activate
merely because a question mentions a country. Only the country and bounded time
interval go upstream; private question text and research phrases do not.

Bounds: one request, no redirects or retries, 20-second outer timeout, the existing
5 MiB transport cap, a tighter 64 KiB ceiling before JSON parsing, at most 14 days
and 15 daily buckets. Repeated/out-of-window buckets, inconsistent denominators,
unexpected dimensions and invalid counters fail collection rather than produce
partial-success claims. Returned events retain the effective measurement period,
each counter, the total-test denominator, country precision and source attribution.
Zero-count/empty responses mean no returned coverage. False-positive anomalies
are possible, and OONI's confirmed category is an upstream heuristic classification,
not this application's independent verification of censorship or cause. See
[OONI's interpretation guidance](https://ooni.org/documents/2021-ooni-partner-training-resources/interpreting-ooni-data.pdf).

The [published data licence](https://github.com/ooni/license/blob/master/data/LICENSE.md)
is **Creative Commons Attribution-NonCommercial-ShareAlike 4.0**. Collection
therefore defaults to `UNAVAILABLE` until the operator acknowledges appropriate
use through the provider's configuration. This implementation does not claim a
commercial-use right. Licence identity and attribution remain in the evidence;
deployment and downstream reuse must preserve the applicable obligations.
The code exposes `allow_noncommercial_data=False` by default. The temporary
development smoke test enabled it for this non-commercial aggregate verification;
it did not change operator settings or persist a report.

Offline verification: `uv run pytest tests/test_ooni_aggregate.py --no-cov -q`,
18 tests passed; Ruff and strict mypy passed. The fixture is synthetic. Tests
cover explicit routing, licence gating, country precision, counter denominators,
rejected extra dimensions and dates, response-size limits, invalid/blocked data,
and exclusion of probe-level fields from output.

## E8: IODA feasibility, deferred

The [IODA API page](https://api.ioda.inetintel.cc.gatech.edu/v2/) embeds its OpenAPI
schema. It documents `GET /v2/outages/summary`, with country, time, result-limit
and extension-window parameters. A normal public request used country `IR`,
4 September 00:00 to 5 September 00:00 UTC (`from=1788480000`,
`until=1788566400`), `limit=1`, `page=0`, and `extendWindow=0`.

HTTP 200 returned 459 bytes of JSON with `type: outages.summary`, `error: null`
and `data: []`. Its copyright field explicitly reserved rights to Georgia Tech
Research Corporation. This check did not establish a positive-record schema or
data reuse permission. No IODA provider was enabled or speculative parser added.
An empty result from this one request does not establish absence of outages.
Next steps are to establish applicable public-data reuse terms and verify a
documented positive country-summary response before implementation.
