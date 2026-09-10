# Existing RSS health snapshot

Checked once on 10 September 2026, **12:50:14 to 12:50:28 UTC**, from the
development host. This is a point-in-time transport and parser check, not a
continuing availability or source-reliability assessment.

**33 of 38 sources parsed successfully**, yielding 1,396 bounded items in total.
Five failed, none timed out and none returned an empty successful feed.

## Failures

| Sources | Observation | Interpretation |
| --- | --- | --- |
| UN News, UN press releases | HTTP 200 followed by `Unsupported response content encoding` | The existing transport requires identity encoding and rejects the upstream encoding before reading the body. Investigate a bounded safe decoder or documented identity response; do not remove decompression-bomb protection. |
| r/worldnews, r/geopolitics, r/UkrainianConflict | HTTP 429 | The public RSS endpoints rate-limited this request. No retries or access workarounds were attempted. |

All 14 world-outlet feeds, all eight regional feeds and all six YouTube feeds
parsed. South China Morning Post followed two ordinary 301 redirects on its
published host before returning valid XML.

## Date coverage matters separately

Six successful feeds produced **311 items without a recognised publication
timestamp**:

| Source | Parsed items |
| --- | ---: |
| GOV.UK FCDO news | 20 |
| GOV.UK foreign travel advice | 20 |
| US State Department travel advisories | 200 |
| International Crisis Group | 10 |
| DW World | 11 |
| Nikkei Asia | 50 |

This does not establish that their upstream records contain no dates. They may
declare an update date rather than publication, or expose a format the existing
parser does not recognise. A date-policy/parser investigation should preserve
that distinction. Do not substitute collection time as publication time. A
provider that parses successfully can still contribute no evidence to a
publication-date-filtered research question.

For successful feeds with recognised publication dates, each feed's newest
parsed dated item was less than three days old. This says nothing about complete
coverage of older material. The existing 200-item ceiling was retained.

## Method and retained data

The audit used the existing `FeedHttpClient` and `RssConnector` with the original
38 source seeds, their options and the genuine configured operator User-Agent.
It admitted at most four sources concurrently, one attempt per source, with a
15-second source deadline, the existing 5 MiB response cap and at most three
normal redirects. Existing public-host checks, DNS pinning, TLS verification
and response-encoding guards remained enabled.

No API keys were sent, no application feed settings changed and no account
actions occurred. The normal application may have polled independently. No
second audit or retry was performed. Article content, titles, summaries, links,
response bodies, contact values and raw exception text were not retained in the
audit artifacts.

## Follow-up code inspection, without another network request

The date handling is intentionally conservative. `feed_source_dates` recognises
explicit RSS `pubDate`, Atom `published` and Dublin Core Terms `issued` as
publication. Atom `updated` is modification; generic Dublin Core `date` is
unspecified. Tests in `test_rss.py` cover those distinctions. A calendar-day-only
publication is retained as a day interval, not a fabricated timestamp.
`ResearchFeedParser` currently requires a non-null `published_at`, so modified,
unspecified and day-only dates are all excluded from its publication query.

The six affected responses were not retained, so this inspection cannot assign
their missing timestamps to a specific field or parser defect. A future bounded
check should record only counts by date-field name, role, parse status and
precision. A safe product improvement is an explicit dated-context policy and
exclusion receipts, not an automatic `updated`-as-publication fallback.

There is also a separate redirect difference: scheduled RSS allows three
validated redirects, while `collect_feed` uses `max_redirects=0`. SCMP's observed
two redirects therefore need a verified canonical seed URL or a trusted static
feed redirect policy before its new on-demand provider can be assumed usable.
Do not widen redirect policy for question URLs or credentialed requests.

The UN failures happen before body consumption, not after HTTPX decompression.
`FeedHttpClient._read_bounded` explicitly rejects non-identity encoding before
calling `aiter_bytes`; `test_feed_http_bounds.py` verifies that encoded bodies
are not consumed. The audit did not retain the exact rejected encoding, so it
does not establish that UN uses gzip rather than Brotli or another encoding.

An existing safe gzip implementation is available in `DigitrafficHttpClient`:
it consumes `aiter_raw`, independently caps compressed and decoded bytes, uses
`zlib.decompressobj` with a maximum output length, and rejects incomplete,
concatenated or trailing streams. A narrowly enabled RSS gzip reader could reuse
that mechanism while preserving the normal contact User-Agent, SSRF checks,
timeouts and source-specific scope. Do not route UN requests through Digitraffic's
client wholesale: that class changes identification headers. Confirm the actual
upstream encoding before implementing a decoder; leave unsupported encodings
fail-closed. No transport or parser changes were made by this audit.

[rss-health.json](rss-health.json) records each source's ID, result count,
recognised date bounds, elapsed time, response size when available, safe HTTP
status/host sequence and classified failure reason. JSON validity and the
38 unique source IDs were verified locally.

## Verified UN encoding and bounded repair

A separately authorised follow-up at **12:54:43 UTC** requested the two exact
UN feed URLs once each and closed after response headers. Both returned HTTP
200 and `Content-Encoding: gzip` despite `Accept-Encoding: identity`. Declared
compressed sizes were 7,087 bytes (UN News) and 2,364 bytes (UN Press). No body
was consumed during those checks and no other sources were re-requested.

The subsequent repair adds `bounded_gzip.py` and a small `FeedHttpClient`
delegation. Only those two exact URLs may use the raw bounded gzip decoder.
Credentialed requests, all redirects (including a redirect back to the same
URL), other URLs and other encodings retain the existing policy. Compressed
and expanded bytes each remain capped by the original client limit. Truncated,
invalid, concatenated and trailing gzip streams fail. The configured User-Agent,
public-host checks, DNS pinning and TLS behaviour are preserved.

The original 38-source result above remains a historical snapshot of the failure
before repair. No date role or publication timestamp behaviour was changed.

The final focused suite passed **77 tests**, covering the new decoder, existing
feed HTTP behaviour, encoding guards, Digitraffic, camera HTTP and RSS parsing.
Combined coverage of the new helper and feed HTTP module was **91.00%**, with
**100% statement and branch coverage for the new helper**. Changed-file Ruff,
formatting, strict mypy and Bandit passed. `http.py` remains 344 lines.

At **13:02:33 to 13:02:34 UTC**, a separately authorised post-repair check made
one complete GET per UN source through the actual RSS adapter:

| Source | HTTP | Parsed items | Recognised publication dates |
| --- | ---: | ---: | ---: |
| UN News | 200 | 30 | 30 |
| UN Press | 200 | 10 | 10 |

Those results are saved separately in `post_repair_un_checks` in the JSON audit.
The original 33/38 baseline has not been overwritten. Other sources were not
re-requested, and the check did not change the running application's settings.
