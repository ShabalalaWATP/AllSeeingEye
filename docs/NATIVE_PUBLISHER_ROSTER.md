# Native publisher roster and translation audit

KAN-131 adds 15 publisher-advertised native-language RSS feeds. The live checks
below ran on **30 September 2026, 02:00 to 02:02 UTC**, using the production
`FeedHttpClient` and `RssConnector`. All included endpoints returned HTTP 200 and
dated items. This establishes one successful snapshot, not continued availability,
editorial independence, accuracy, or permission for broader republication.

The seeds in `backend/src/ase/resources/feeds/rss_native.json` retain headlines,
attribution, dates and links only. They exclude summaries, article text and imagery.
They have explicit F6 unassessed ratings and preserve the configured native language.
No coordinates are inferred from a publisher, language or routing country.

## Included feeds

The [machine-readable evidence](evidence/native_publisher_probes_2026_09_30.json)
records the exact feed URL, discovery URL, HTTP status, UTC observation time, parsed
item count, newest publication date and reuse limitation for every included feed.
Counts below are accepted parser items, capped at 200, not a publisher archive size.

| Seed | Language | Items | Newest publication, UTC | Publisher discovery |
| --- | --- | ---: | --- | --- |
| `bbc_arabic` | Arabic | 23 | 2026-09-30 00:38:49 | [BBC feed register](https://github.com/bbc/world-service-rss/blob/main/index.js) |
| `bbc_hindi` | Hindi | 37 | 2026-09-30 01:30:20 | BBC feed register |
| `bbc_urdu` | Urdu | 21 | 2026-09-29 16:48:33 | BBC feed register |
| `bbc_japanese` | Japanese | 38 | 2026-09-29 13:20:50 | BBC feed register |
| `bbc_korean` | Korean | 21 | 2026-09-29 07:01:12 | BBC feed register |
| `bbc_hausa` | Hausa | 34 | 2026-09-29 17:56:49 | BBC feed register |
| `bbc_swahili` | Swahili | 42 | 2026-09-29 16:29:30 | BBC feed register |
| `bbc_afrique` | French, Africa edition | 35 | 2026-09-29 17:43:31 | BBC feed register |
| `trt_haber_tr` | Turkish | 60 | 2026-09-29 17:43:00 | [TRT RSS directory](https://www.trthaber.com/sitene_ekle.html) |
| `ndtv_hindi` | Hindi | 100 | 2026-09-30 01:10:58 | [NDTV RSS directory](https://www.ndtv.com/rss) |
| `express_urdu` | Urdu | 50 | 2026-09-29 18:45:19 | [Express RSS page](https://www.express.pk/rss/) |
| `radio_okapi_fr` | French, DRC focus | 50 | 2026-09-29 19:40:26 | [Radio Okapi feed notice](https://www.radiookapi.net/content/fil-rss) |
| `deutschlandfunk_de` | German | 24 | 2026-09-30 01:56:53 | [Deutschlandfunk RSS directory](https://www.deutschlandfunk.de/rss-angebot-102.html) |
| `anadolu_ar` | Arabic | 30 | 2026-09-29 20:53:44 | [Anadolu Arabic homepage RSS link](https://www.aa.com.tr/ar) |
| `maariv_he` | Hebrew | 100 | 2026-09-29 20:32:22 | [Maariv RSS directory](https://www.maariv.co.il/rss) |

The eight BBC editions share the existing `BBC` organisation key. Anadolu Arabic
shares `Anadolu Agency` with its English edition. Multiple editions do not supply
independent corroboration. Native language is configured from the publisher's
edition, not automatically verified for every item. Some publishers syndicate
stories from the same upstream agency.

All rows use the same conservative licence note: publisher-supplied public RSS,
headlines and links only, broader reuse rights not established, publisher terms
apply. Discovery pages are not open-content licence grants. In particular,
[NDTV's feed terms](https://www.ndtv.com/rss) and
[Maariv's terms](https://www.maariv.co.il/terms-of-use) remain publisher conditions.
This change adds no article scraper, paywall access, licence override or public
republication claim. Existing provider attribution remains attached to evidence.

## Routing and capacity

Each new seed enters the existing regional feed and research factories, with an
explicit reviewed allocation profile. `native_regions.py` lists editorial coverage
countries for routing; this is not a claim that every returned headline concerns
that country. Research still requires an explicit phrase, compatible language and
publication interval. An explicit source override permits deliberate cross-region
selection. Broader African and Arabic editions can route to several reviewed
countries without assigning those countries to the event.

The baseline has 134 executable research providers. These 15 make 149. The sibling
sources batch adds five further providers, making an expected 154 of the unchanged
160-provider ceiling. The combined branch must verify that final count; it is not
evidence of a combined run in this worktree.

## Translation policy and real-time measurement

Every new seed sets `translate_on_demand: true` in its RSS options. The connector
adds the `translate_on_demand` event tag and the ordinary background queue excludes
it, including cache hits. Native titles remain available to explicit research;
this change does not add a manual-translation UI or promise translated titles.
The existing automatic limit remains 20 titles per call and 60 calls per hour.
That is a maximum batch capacity, not measured model throughput.

The audit tool runs the actual parser, bounded memory store and translation queue
against only this roster. A sentinel fails if any automatic translation is
attempted. It does not connect to an installation database, model or credentials,
and does not measure other installed feeds or model latency. It writes only
aggregate observations, never article URLs, titles, bodies or raw feed snapshots.

From `backend`, run a single read-only live check into a new report path:

```powershell
uv run python -m ase.container.native_feed_audit --once --output .pytest_cache/native-smoke.json
```

For the elapsed 24-hour observation, omit `--once` and keep the process running:

```powershell
uv run python -m ase.container.native_feed_audit --output .pytest_cache/native-24h.json
```

Each publisher is fetched at the seeds' 30-minute interval, using normal DNS/IP,
redirect, TLS, byte and timeout guards. Requests to a shared host are spaced.
Existing output files are refused. Aggregate output is replaced atomically after
each round and on exit. Interruption records an incomplete observation.

`completed_24_hours` requires elapsed monotonic time, all 49 scheduled rounds,
no excessive gap, no feed failures, at least one non-empty response per source,
no identity-counter saturation and no automatic model attempt. Sleep, one initial
snapshot or a fake-clock test cannot establish live completion. Repeated item
observations are distinguished from unique item identities. Revisions to the same
identity are not counted as additional unique arrivals.

**The genuine 24-hour run remains outstanding.** Offline duration tests verify the
tool's reporting contract only. Do not remove translation-on-demand flags based on
a smoke report, and do not describe this isolated audit as installation-wide usage.

## Deferred or rejected candidates

| Candidate | Observation or decision |
| --- | --- |
| [Kan](https://www.kan.org.il/), [Davar](https://www.davar1.co.il/), [Zman Israel](https://www.zman.co.il/) | Each homepage returned HTTP 403 to the normal client. No bypass or inferred feed path was used. Maariv supplies the initial Hebrew feed. |
| [Israel Hayom](https://www.israelhayom.co.il/) | Homepage exceeded the normal 5 MiB response cap. The cap was not raised. |
| [OneIndia Hindi](https://hindi.oneindia.com/rss) | Advertised directory returned HTTP 403 to the normal client. |
| [Tagesschau](https://www.tagesschau.de/infoservices/rssfeeds) | Current directory describes private/non-commercial restrictions and separate publishing arrangements. Not added in this slice. |
| [Walla](https://news.walla.co.il/rss) | Directory states private-use restrictions; no broader reuse permission established. |
| NHK Japanese, DW German | No exact, currently advertised native feed URL was established from the inspected publisher page. No third-party URL guess was enabled. |
| KBS Korean | Inspected Korean directory advertised entertainment; the desired general-news feed was not established. BBC Korean is included. |
| Asahi Japanese | Publisher directory found, but not live-probed or enabled in this bounded slice. |
| BBC Turkish | Live HTTP 200, 21 items, newest 2026-09-29 23:08:07 UTC. Omitted to limit BBC duplication because TRT Turkish is included. |
| Radio Farda | Live HTTP 200, 20 items, newest 2026-09-30 01:30:00 UTC. Deliberately not enabled until reuse scope is established. |

Radio Farda is no longer an unprobed candidate: its
[publisher RSS directory](https://www.radiofarda.com/rssfeeds) advertises `/api/`,
which passed the same parser/client check. It is RFE/RL's Persian service, not an
Iranian government source. A [US Senate letter dated 10 April 2026](https://www.blumenthal.senate.gov/newsroom/press/release/amidst-ceasefire-negotiations-blumenthal-calls-on-trump-administration-to-fully-restore-voa-persian-and-radio-farda-broadcast-to-iran)
describes USAGM grant-funding and resource concerns. That dated political context
does not establish current funding amounts, editorial reliability or a reuse
licence. The decision for this roster is exclusion, with current endpoint evidence
preserved. No claim is made that public funding places the content in the public
domain. Existing Persian feeds continue to provide the earlier bounded coverage.

## Validation and integration

Offline tests cover strict options, all seed ratings/languages, shared ownership,
RSS-to-event policy propagation, automatic/cache translation exclusion, network
refusal and SSRF preservation, aggregate-only probe output, elapsed-time audit
gates, and regional factory/allocation composition. Live evidence is kept separate
from these fixtures. The final sources batch must rerun allocation/capability tests
and reconcile its profile-file split and provider-count assertion.

Validation on this branch: 195 focused backend tests passed. After the final
country-label adjustment, 57 composition/language tests passed again. Changed-file
Ruff checks, strict mypy (nine source files), three import-linter contracts, Bandit
and the 400-line check passed. The two-line allocation hook temporarily leaves the
existing profile file above the 350-line target; the sibling sources batch already
splits that file and owns its final composition. Coverage was not measured.

The executable `--once` audit at 02:09:29 to 02:09:43 UTC recorded 665 on-demand
item observations, 664 distinct IDs, zero feed failures and zero unexpected model
attempts. It reported 13.646 elapsed seconds and `completed_24_hours: false`.
This is a smoke check, not the outstanding full-duration acceptance run.
