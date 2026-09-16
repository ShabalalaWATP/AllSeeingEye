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

Twenty-six public feeds supply the economic panels, all verified live on
16 September 2026:

- **United Kingdom:** [Bank of England](https://www.bankofengland.co.uk/rss/news),
  [HM Treasury](https://www.gov.uk/government/organisations/hm-treasury.atom),
  [ONS releases](https://www.ons.gov.uk/releasecalendar?rss)
- **United States:** [Federal Reserve](https://www.federalreserve.gov/feeds/press_all.xml),
  BLS [consumer prices](https://www.bls.gov/feed/cpi.rss),
  [employment](https://www.bls.gov/feed/empsit.rss) and
  [producer prices](https://www.bls.gov/feed/ppi.rss),
  [Census economic indicators](https://www.census.gov/economic-indicators/indicator.xml),
  [EIA Today in Energy](https://www.eia.gov/rss/todayinenergy.xml)
- **Multilateral and other central banks:**
  [ECB](https://www.ecb.europa.eu/rss/press.html),
  [BIS speeches](https://www.bis.org/doclist/cbspeeches.rss),
  [WTO](https://www.wto.org/library/rss/latest_news_e.xml),
  [Bank of Japan](https://www.boj.or.jp/en/rss/whatsnew.xml),
  [Bank of Canada](https://www.bankofcanada.ca/content_type/press-releases/feed/),
  [Reserve Bank of India](https://www.rbi.org.in/pressreleases_rss.xml),
  [Bank of Russia](https://www.cbr.ru/rss/EngRssPress)
- **Publishers:** [BBC Business](https://feeds.bbci.co.uk/news/business/rss.xml),
  [Guardian business](https://www.theguardian.com/uk/business/rss),
  [The Economist finance and economics](https://www.economist.com/finance-and-economics/rss.xml),
  [DW Business](https://rss.dw.com/rdf/rss-en-bus),
  [France 24 Business](https://www.france24.com/en/business/rss),
  [bne IntelliNews](https://www.intellinews.com/feed/),
  [The Bell](https://en.thebell.io/feed/),
  [SCMP China economy](https://www.scmp.com/rss/318421/feed/),
  [CGTN Business](https://www.cgtn.com/subscribe/rss/section/business.xml),
  [Tehran Times economy](https://www.tehrantimes.com/rss/tp/697)

Successful HTTP access does not guarantee fresh content, and stale or undated items
are excluded from recent headlines. Only headline metadata and links are collected;
publisher terms remain visible in the catalogue. Public access does not establish
unrestricted commercial republication rights.

### Which headlines count as economic

General business feeds carry lifestyle and technology features beside economic
reporting: a two-day window in September 2026 led with banned app advertising,
aircraft window engineering and first-week-at-work advice. `domain/economy_relevance.py`
judges every headline with readable rules and no model call, so the same headline always
produces the same verdict and an excluded story can be argued with:

- A feature or lifestyle framing never qualifies, whoever published it.
- An official economic issuer's own release qualifies by the nature of its feed.
- Everything else needs at least one core subject-matter phrase from
  `domain/economy_lexicon.py` (inflation, interest rates, growth, jobs, trade, tariffs,
  currencies, bonds, budgets, debt, energy prices, markets, company finances). Company
  names, institutions and figures raise the rank but never carry a headline alone, so
  "Complaints to watchdog about water firms jump 84%" is still refused.

Each kept item shows the reason it was kept. The panel reports how many headlines
reached the window and how many carried economic substance, so a quiet window reads as
quiet rather than broken. Official data releases rank above market reporting, which ranks
above general coverage, and each feed takes one turn per round so no publisher fills the
panel.

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

## Operational and security boundaries

`GET /api/economy`, `GET /api/economy/news?days=2` and `POST /api/economy/briefing?days=2`
require a current authenticated session. Public collection happens outside the
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
