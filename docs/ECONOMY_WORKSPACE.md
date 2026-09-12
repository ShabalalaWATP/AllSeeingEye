# Economy and personal workspace

## Navigation

The main sidebar contains Map, Research, Subscriptions, Geolocation and Economy.
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
| World Bank Indicators API | GDP, growth, inflation and unemployment for the six focus regions | Annual observations, up to 12 years; shared 24-hour cache. Latest available year may differ by country and measure. |
| European Central Bank | GBP, USD and CNY per euro | Daily reference rates, up to 90 days; shared one-hour cache. RUB is suspended and IRR is not published. |
| Publisher RSS | Economic headlines, dates and source links | Existing bounded feed collection; dashboard shows the past 72 hours with known publication dates. |
| TradingView embedded chart | Selected equity, currency, commodity and index-proxy instruments | Explicit browser opt-in. Timing depends on the instrument, with delayed or end-of-day equities and clearly labelled CFD proxies. |

Official documentation: [World Bank Indicators API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation),
[World Bank data terms](https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets),
[ECB reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html),
[TradingView chart widget](https://www.tradingview.com/widget-docs/widgets/charts/advanced-chart/)
and [TradingView data availability](https://www.tradingview.com/widget-docs/faq/data/).

The instrument list deliberately contains only verified symbols. US 500 and UK
100 are labelled CFD proxies, not official exchange index feeds. Russia and Iran
have economic statistics and reporting, but no supported direct local-equity
chart in this selection. The app does not substitute unrelated prices.

The external chart loads only after the user selects Load market charts. The
disclosure explains that TradingView receives the browser connection and public
symbol. It receives no application token, question, report or account identity.
One fixed-origin sandboxed iframe is active at a time. Hidden tabs suspend it;
Stop charts unmounts it. Login changes clear the local opt-in. The server CSP
allows only the documented widget frame origin, without adding external scripts
to the parent page. TradingView attribution remains visible.

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

## Daily AI analysis

Opening Economy admits one personal Deep research briefing covering worldwide
developments and the five countries. It uses the existing cited professional
report pipeline, with full-report and Word, PDF and Markdown export links. The
page shows progress, a readable summary, references and the next refresh time.
The request asks for plain explanations, comparisons, uncertainty and coverage
gaps. It does not request investment recommendations or invented market prices.

The same durable job is reused for 24 hours, including failed and paused work.
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

## Operational and security boundaries

`GET /api/economy`, `GET /api/economy/news` and `POST /api/economy/briefing`
require a current authenticated session. Public collection happens outside the
source lock; final source filtering, session revalidation and response construction
hold the source admission guard. Disabling a source during a request therefore
prevents its release. Personal report ownership is checked by the existing jobs
and report services before preparation, persistence and delivery.

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
