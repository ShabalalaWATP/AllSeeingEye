# Economy and personal workspace

## Navigation

The main sidebar contains Map, Research, Subscriptions, Geolocation, Economy and
Cyber intelligence. See [the cyber workspace guide](CYBER_THREAT_INTELLIGENCE.md).
Research contains New research, Saved reports, Daily briefing and Plans & areas.
The profile icon opens identity, security and team sharing. The settings icon
opens personal preferences and links to the source catalogue and alert rules.
Existing direct routes remain usable. Administration remains a separate guarded
workspace with its own navigation.

Personal settings include Obsidian, Slate and Daylight themes, reduced motion,
time and region preferences, research defaults and report preferences. Values are
stored in the authenticated user's existing profile JSON. Themes reset on logout
and do not alter another account. Reduced motion also disables eye motion and
globe auto-rotation. Map colours remain legible independently of the page theme.

## Dashboard

Worldwide economic headlines appear first. Global, UK, USA, Russia, China and
Iran focus controls select market instruments, official economic indicators and
regional reporting. Country tags represent subject matter or publisher remit,
not verified incident coordinates. The page explains unfamiliar measures and
offers accessible history charts with exact data tables. Missing observations
remain gaps, never zeroes.

| Source | Content | Refresh and limits |
| --- | --- | --- |
| World Bank Indicators API | Twelve measures covering output, people, prices, jobs, trade, industry, investment and central government debt | Six regions, up to 12 annual observations each; shared 24-hour cache. Latest available year may differ by country and measure. |
| European Central Bank | GBP, USD and CNY per euro | Daily reference rates, up to 90 days; shared one-hour cache. RUB is suspended and IRR is not published. |
| Publisher RSS | Economic headlines, dates and source links | Select 2, 5, 7 or 14 days. Only known publication dates inside the selected period appear; economic cache retention is 14 days, within existing item and global memory caps. |
| TradingView embedded chart | Selected equity, currency, commodity and index-proxy instruments | Loads automatically. Timing depends on the instrument, with delayed or end-of-day equities and clearly labelled CFD proxies. |

Official documentation: [World Bank Indicators API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation),
[World Bank data terms](https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets),
[ECB reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html),
[TradingView chart widget](https://www.tradingview.com/widget-docs/widgets/charts/advanced-chart/)
and [TradingView data availability](https://www.tradingview.com/widget-docs/faq/data/).

The instrument list deliberately contains only verified symbols. US 500 and UK
100 are labelled CFD proxies, not official exchange index feeds. Russia and Iran
have economic statistics and reporting, but no supported direct local-equity
chart in this selection. The app does not substitute unrelated prices.

The external chart loads automatically, as requested. The provider details
explain that TradingView receives the browser connection and public
symbol. It receives no application token, question, report or account identity.
One fixed-origin sandboxed iframe is active at a time. Hidden tabs suspend it;
Stop charts unmounts it and Resume charts restores it. Login changes reset
the selected instrument and pause state. The server CSP
allows only the documented widget frame origin, without adding external scripts
to the parent page. TradingView attribution remains visible.

## Data analysis and comparisons

Country profiles start with a short source-linked overview of the available
growth, prices, employment and external-balance observations. Each value keeps
its own observation year. Unavailable retained points are excluded from narrative
analysis, and historical/cached data remains distinct from recent reporting.
Calculated insights separate the recorded fact from its explanation.

Country profiles show all twelve miniature histories automatically, grouped by
output/living standards, prices/jobs, trade/industry and public finances/investment.
Selecting an indicator opens its larger chart, source and exact data table.
Coverage counts distinguish available and missing series. Old observation years
and cached snapshots remain labelled.

The expanded indicators are GDP per capita (`NY.GDP.PCAP.CD`), population
(`SP.POP.TOTL`), goods/services exports and imports as shares of GDP
(`NE.EXP.GNFS.ZS`, `NE.IMP.GNFS.ZS`), current account balance (`BN.CAB.XOKA.GD.ZS`),
central government debt (`GC.DOD.TOTL.GD.ZS`), gross capital formation
(`NE.GDI.TOTL.ZS`) and manufacturing value added (`NV.IND.MANF.ZS`). These supplement
the existing GDP, growth, inflation and unemployment measures. Each metric links
to its World Bank definition. Debt coverage is central government, not necessarily
all public bodies. Investment includes inventories. Nominal dollar changes are
not real economic growth or household earnings.

Calculated country insights use the supplied observations and source links, not
generated guesses. Annual changes require adjacent years: rates and GDP shares
use percentage points, while amounts use relative percentage change only from a
positive base. Missing years are not interpolated. Inflation easing can still
mean consumer prices rose. No composite health score or forecast is fabricated.

Compare economies uses one indicator, unit and year across the five countries.
The default chooses the year with widest coverage, breaking ties by recency.
Users can choose another year; missing values remain explicit. Rankings describe
only countries with observations for that period. Worldwide benchmarks are the
provider's aggregates, not averages of the five countries. The underlying table
retains values, preceding-year observations and source links.

Currency movement analysis calculates quote units per base currency by dividing
their ECB-per-euro rates on matching dates. EUR uses an exact reference of one.
No rate is forward-filled or derived from non-positive inputs. The 30/90-day
window ends at the latest matching date, with observed low/high, count and date
shown. Change equals `(last / first - 1) * 100`; a rise means the base currency
strengthened against the quote. One observation cannot produce a period change.
These are daily reference calculations, not intraday extremes or executable
quotes. Provider methodology: [ECB reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html).

## Economic reporting

Nine public feeds supplement the existing source catalogue:

- [BBC Business](https://feeds.bbci.co.uk/news/business/rss.xml)
- [The Guardian business](https://www.theguardian.com/uk/business/rss)
- [Bank of England news](https://www.bankofengland.co.uk/rss/news)
- [HM Treasury announcements](https://www.gov.uk/government/organisations/hm-treasury.atom)
- [Federal Reserve releases](https://www.federalreserve.gov/feeds/press_all.xml)
- [Bank of Russia releases](https://www.cbr.ru/rss/EngRssPress)
- [SCMP China economy](https://www.scmp.com/rss/318421/feed/)
- [CGTN Business](https://www.cgtn.com/subscribe/rss/section/business.xml)
- [Tehran Times economy](https://www.tehrantimes.com/rss/tp/697)

All nine responded successfully to the development probes on 12 September 2026.
Successful HTTP access does not guarantee fresh content: CGTN was stale during
the probe and HM Treasury omitted publication dates in the examined entries.
Stale or undated items are excluded from recent headlines. Only headline metadata
and links are collected; publisher terms remain visible in the catalogue. Public
access does not establish unrestricted commercial republication rights.

New sources default to unassessed F6. Official releases and state-aligned
perspectives are labelled, not automatically promoted in credibility. Existing
publisher organisation keys keep business and general feeds from the same
publisher from being counted as independent corroboration.

## Reporting periods and AI summaries

The summary-period control offers 2 Day, 5 Day, 7 Day and 14 Day, defaulting to
2 Day. It applies to news and the personal Deep research briefing covering
worldwide developments and the five countries. The URL preserves the selected
period when changing country. Annual indicators and the currency chart retain
their separately labelled observation dates and controls.

Each report shows its exact frozen start and end dates. News shows its own
snapshot window, which can advance after the report was prepared. The 24-hour
refresh cycle is independent of the number of days covered. News uses publication
times, never a recent retrieval time as a substitute for an old publication.

The briefing uses the existing cited professional
report pipeline, with full-report and Word, PDF and Markdown export links. The
page presents an executive paragraph, distinct key points, themed developments,
readable country assessments, conditions to watch and references. The full report
remains available. The worldwide news section starts with a cited briefing
takeaway above six stories. Regional reporting reuses the opening cited country
paragraph. While the briefing is unavailable, these introductions attribute the
leading available headlines rather than invent an analysis. The request asks for
plain explanations, comparisons, uncertainty and coverage gaps, not investment
recommendations or invented market prices.

The same durable job is reused for 24 hours per user and reporting period,
including failed and paused work. Switching period starts or reuses that period's
job and immediately hides the old report; late responses cannot overwrite it.
It refreshes when the page is visible or on the next eligible visit. Use
Subscriptions for unattended scheduled research while the server is running.
Ordinary data refresh does not regenerate the AI report. The existing configured
AI connection, report limits and access rules apply.

The briefing can freeze six regional World Bank snapshots and three available
ECB series as cited background context, alongside selected economic reporting.
Observation periods, retrieval times and provider update dates remain separate.
Unknown publication times remain unknown; a recent fetch never makes a historical
statistic a new event. Macro context is admitted through an explicit dated-context
selection. The model cannot read or quote the external market chart.

The reporting-period identities are distinct from the former one-day briefing.
Existing saved reports remain accessible, and their original admission markers
retain deletion protection. The first visit to a new period can create a new
briefing. Repeated visits, country switches and public-panel refreshes reuse it.

A 14-day selection cannot restore articles no longer supplied by a publisher or
lost on a process restart. The economic feed cache retains at most 14 days and
5,000 items, subject to the existing global memory cap. Historical source coverage
remains explicit; these windows do not promise a complete publisher archive.

Internally assembled economic snapshots receive a bounded 2,000-character source
summary budget so later indicators do not disappear under the ordinary 600-character
headline limit. Exact source, category and record-kind checks restrict this
exception. Twelve-year numerical histories fit in the frozen evidence attributes;
the model text carries the latest two available observations and their dates.
Each regional snapshot remains within 38 attributes and the existing value bounds.
The expanded public probe returned 864 rows in 197,553 bytes, within the unchanged
512 KiB HTTP cap.

## Plain-English explainer

A separate, lighter feature from the Deep research briefing above. It writes short
plain-English paragraphs explaining what the figures already on the page mean, for
readers who are not finance experts. It never replaces the figures, never runs the
cited report pipeline and never produces a downloadable report.

### What the model is given

One compact grounded fact pack is built from the current snapshot. Per region it
carries each of the twelve indicators with its latest value, observation year and
unit; the previous observation and the change, stated explicitly as a percentage
change or a percentage-point change; years inside the published range with no
observation; the series status (available, stale or unavailable); counts of
indicators with and without data; the ECB reference rates with their observation
dates; and up to five recent dated economy headlines with their publisher names.
No links, article bodies, retrieval times or raw events reach the model. The prompt
tells the model to build on the indicator figures, which are the reliable part of
the evidence, and to mention a headline only when it is clearly about growth,
prices, jobs, trade, energy, public finances, business or currencies, because the
publisher feed can carry soft features that are not economic.

The prompt rules require UK English, no em dashes, everyday words with any
unavoidable term explained in the same sentence, no invented numbers, no forecast
stated as fact, no live market claim, plain statements when data is old or missing,
and a clear separation between what the figures show and a possible reason for it.
The supplied facts are stated to be data, never instructions.

### Cadence and cost

At most one model call per fact-pack fingerprint, and never more often than once in
24 hours, whichever is longer. The fingerprint is a SHA-256 of the canonical facts
excluding the retrieval time, so a refetch that changes nothing spends nothing. A
rejected answer is retried once with the rejection reasons, so one generation costs
at most two calls. The completion budget is capped at 6,000 tokens and the fact pack
is roughly 4,000 prompt tokens, so an ordinary day is one call of about 4,000 prompt
and 2,000 to 4,000 completion tokens, and the realistic worst case is about 20,000
tokens a day. Every call is reserved and settled through the AI allowance ledger with
system attribution and the purpose `economy_explainer`; see
`docs/adr/0019-ai-usage-allowances.md`.

Generation is serialised by a process-local admission lock, so two readers cannot
generate at once. An ordinary signed-in reader's `GET` may start one generation only
when nothing matching the current fingerprint is cached and the cadence allows it.
Everyone else is served the cached text.

### Mechanical validation

Nothing generated is stored or shown until it passes checks against the supplied
facts:

- every number must match a supplied figure within the rounding the writer used, at
  any readable scale, so a value may be written in full or in thousands, millions,
  billions or trillions;
- every four-digit year must appear in the supplied observation years, gap years,
  reference-rate dates or headline dates;
- region keys must be the six known regions, and every supplied region must be
  written;
- no web address, link, angle bracket, HTML entity, em dash or en dash;
- paragraph counts, list counts and character bounds per section and for the
  glossary;
- listed jargon, for example current account, real terms, basis points or
  quantitative easing, must be explained in the same sentence. The glossary is
  exempt from that check because it is itself the explanation.

On failure the errors are sent back to the model for one retry. If the retry also
fails, nothing is stored and the page says the written summary could not be checked
against the figures. Sign is not checked mechanically: magnitudes are compared, so
the direction words remain the model's own wording under the prompt rules.

### Storage

`economy_explainers` (migration `0056`) is a small operational aggregate holding the
fingerprint, the window start, the checked payload as JSON, the model name, the
generation time, the snapshot retrieval time and the reported prompt and completion
tokens. At most the newest two rows are kept; older rows are deleted on each save.
Prompts and fact packs are never stored. A row whose payload no longer parses within
bounds is treated as absent rather than shown.

### What a reader sees

"The world economy right now" leads the page with the takeaway as a strong lead line,
two or three short paragraphs at a readable measure, and compact "What is driving it"
and "What to watch" lists. Each country summary sits beside that country's figures,
with the takeaway and first paragraph always visible and any remaining paragraphs
behind a native disclosure. Every indicator carries a keyboard usable "What does this
mean?" disclosure showing the project's careful `INDICATOR_NOTES` explanation first
and, underneath and labelled as model-written, the model's everyday wording for the
same term. The careful note therefore always wins a disagreement.

Every panel states that it was written by the model from the figures on the page,
that the figures are the source of truth, the model name, the generation time and the
snapshot retrieval time. Administrators additionally see a Rewrite summary control.
While a checked summary exists it supersedes the templated headline lead in the news
panels; that template remains only as a fallback when neither a checked summary nor a
cited briefing paragraph is available.

| State | What the page shows |
| --- | --- |
| `ready` | The summary, with the figures beside it |
| `stale` | The previous summary plus a "Figures moved on" badge and a note that a fresh version is written at most once a day |
| `generating` | An "Updating" badge and a note that a fresh summary is being written |
| `empty` | A note that nothing has been written yet; the figures are unaffected |
| `unavailable` | The honest reason, either no assigned model or a spent AI allowance; never an error page |
| `validation_failed` | A note that the summary failed its checks and was discarded, with the figures only |

Panels are responsive from 360 pixels, use the existing theme tokens, render
structured React text rather than HTML from data, and carry no animation.

## Operational and security boundaries

`GET /api/economy`, `GET /api/economy/news?days=2`,
`POST /api/economy/briefing?days=2`, `GET /api/economy/explainer` and
`POST /api/economy/explainer/refresh` require a current authenticated session; the
refresh additionally requires an administrator and is audited as
`economy_explainer_refreshed` with the resulting state. The explainer read is rate
limited per account like the dashboard read, 30 requests a minute, and the
administrator refresh is limited to three an hour. Public collection happens outside the
source lock; final source filtering, session revalidation and response construction
hold the source admission guard. Disabling a source during a request therefore
prevents its release. Personal report ownership is checked by the existing jobs
and report services before preparation, persistence and delivery.

The two period-aware endpoints validate `days` against 2, 5, 7 and 14. Briefing
responses return `window_days`, `period_from` and `period_to` from authorised
frozen job input. These fields do not widen the generic progress response or
change Live Monitor's existing behaviour.

World Bank and ECB requests use fixed URLs, bounded responses, finite-value
validation and hardened XML parsing. Each provider has one in-flight request,
timeouts and a retry cooldown. Retained stale data expires after seven days for
annual indicators and three days for FX. Source controls apply to both dashboard
data and briefing context. Raw macro histories remain in bounded shared memory;
only evidence frozen into a report is persisted. No new credentials, database
migration, external account or paid market-data service is required.

Frontend data refresh runs every five minutes while visible, using the shared
server caches. Native indicator charts have bounded points and no charting
dependency. The market iframe is isolated from map rendering. Fixture tests and
public-source probes validate integration boundaries; real-model analysis quality
and long-term feed reliability still need operator evaluation.
