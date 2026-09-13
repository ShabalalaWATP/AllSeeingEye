# Public news RSS verification, 13 September 2026

## Map geography companion

The separate `gdelt_news` bulk-event connector adds geographic reporting signals
without changing the RSS count below. A bounded live connector check on
13 September 2026 returned 400 linked records: 272 city, 63 administrative-area
and 65 country-level locations. These are machine-coded, unverified action
geographies, not publisher headquarters or inferred RSS headline locations.
The source supplies indexing time, not publisher publication time. See
[map news behaviour](MAP_NEWS_AND_EVIDENCE.md#geocoded-reporting) and the
[GDELT event codebook](https://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf).

## RSS verification

Added 38 public feeds: 14 UK national/regional and 24 worldwide, taking the seeded RSS catalogue from 54 to 92. Verification used bounded public feed requests, then the actual NewsRssConnector and Normaliser. The final run yielded 1,506 dated, linked F6 records, with no retained summaries or inferred points. Live endpoint success is a snapshot, not an uptime or publisher-reliability guarantee.

Each source polls at most every 30 minutes. Existing shared limits remain: 200 parsed items per feed, 5 MiB response cap, normalisation/deduplication, scheduler concurrency, 72-hour/40,000-item news retention and 512 MiB store budget. The additional schedule is 76 feed requests per hour before backoff or source controls.

These sources add retained-feed research evidence. They do not enlarge the private publisher-provider inventory (37) or provide fresh private publisher search or a historical archive. All have explicit unassessed source-rating records, F6 item grades, headline/attribution/date/link-only collection and no incident geography inferred from publisher coverage. Shared organisations retain shared independence keys.

| Source ID | Publisher / coverage | Organisation | Language | Feed | Items | Newest publisher date (UTC) |
| --- | --- | --- | --- | --- | ---: | --- |
| `news_bbc_uk` | BBC News UK | BBC | en | [RSS](https://feeds.bbci.co.uk/news/uk/rss.xml) | 24 | 2026-09-12 23:06:08 |
| `news_sky_uk` | Sky News UK | Sky Group | en | [RSS](https://feeds.skynews.com/feeds/rss/uk.xml) | 10 | 2026-09-12 14:53:00 |
| `news_guardian_uk` | The Guardian UK news | Guardian Media Group | en | [RSS](https://www.theguardian.com/uk-news/rss) | 45 | 2026-09-12 18:35:33 |
| `news_independent_uk` | The Independent UK | Independent Digital News and Media | en | [RSS](https://www.independent.co.uk/news/uk/rss) | 20 | 2026-09-12 23:01:00 |
| `news_stv_scotland` | STV News Scotland | STV Group | en | [RSS](https://news.stv.tv/feed) | 50 | 2026-09-12 17:48:10 |
| `news_bbc_scotland` | BBC News Scotland | BBC | en | [RSS](https://feeds.bbci.co.uk/news/scotland/rss.xml) | 23 | 2026-09-12 20:36:14 |
| `news_bbc_wales` | BBC News Wales | BBC | en | [RSS](https://feeds.bbci.co.uk/news/wales/rss.xml) | 27 | 2026-09-12 21:01:54 |
| `news_bbc_northern_ireland` | BBC News Northern Ireland | BBC | en | [RSS](https://feeds.bbci.co.uk/news/northern_ireland/rss.xml) | 47 | 2026-09-12 23:01:08 |
| `news_herald_scotland` | The Herald Scotland | Newsquest | en | [RSS](https://www.heraldscotland.com/news/homenews/rss/) | 50 | 2026-09-12 20:00:00 |
| `news_wales_online` | WalesOnline | Reach plc | en | [RSS](https://www.walesonline.co.uk/news/?service=rss) | 25 | 2026-09-12 21:58:19 |
| `news_belfast_live` | BelfastLive | Reach plc | en | [RSS](https://www.belfastlive.co.uk/news/?service=rss) | 25 | 2026-09-12 19:37:31 |
| `news_manchester_evening` | Manchester Evening News | Reach plc | en | [RSS](https://www.manchestereveningnews.co.uk/news/?service=rss) | 25 | 2026-09-12 21:38:00 |
| `news_birmingham_live` | BirminghamLive | Reach plc | en | [RSS](https://www.birminghammail.co.uk/news/?service=rss) | 25 | 2026-09-12 21:55:23 |
| `news_northern_echo` | The Northern Echo | Newsquest | en | [RSS](https://www.thenorthernecho.co.uk/news/rss/) | 50 | 2026-09-12 19:00:00 |
| `news_cbc_canada` | CBC News top stories | CBC/Radio-Canada | en | [RSS](https://www.cbc.ca/webfeed/rss/rss-topstories) | 20 | 2026-09-12 20:46:38 |
| `news_npr_world` | NPR World | NPR | en | [RSS](https://feeds.npr.org/1004/rss.xml) | 10 | 2026-09-12 13:03:20 |
| `news_pbs_news` | PBS News headlines | NewsHour Productions | en | [RSS](https://www.pbs.org/newshour/feeds/rss/headlines) | 20 | 2026-09-12 21:25:55 |
| `news_nytimes_world` | The New York Times World | The New York Times Company | en | [RSS](https://rss.nytimes.com/services/xml/rss/nyt/World.xml) | 54 | 2026-09-12 22:46:12 |
| `news_rfi_en` | RFI English | France Médias Monde | en | [RSS](https://www.rfi.fr/en/rss) | 22 | 2026-09-12 19:09:06 |
| `news_rfi_fr` | RFI French | France Médias Monde | fr | [RSS](https://www.rfi.fr/fr/rss) | 24 | 2026-09-12 22:41:26 |
| `news_euronews` | Euronews | Euronews | en | [RSS](https://www.euronews.com/rss?level=theme&name=news) | 50 | 2026-09-12 16:00:29 |
| `news_el_pais` | El País Spanish | PRISA | es | [RSS](https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada) | 147 | 2026-09-12 22:58:10 |
| `news_publico_pt` | Público Portugal | Público | pt | [RSS](https://feeds.feedburner.com/PublicoRSS) | 10 | 2026-09-12 21:07:26 |
| `news_france24_ar` | France 24 Arabic | France Médias Monde | ar | [RSS](https://www.france24.com/ar/rss) | 23 | 2026-09-12 20:32:17 |
| `news_africanews` | Africanews | Euronews | en | [RSS](https://www.africanews.com/feed/rss) | 50 | 2026-09-12 15:32:33 |
| `news_premium_times` | Premium Times Nigeria | Premium Times | en | [RSS](https://www.premiumtimesng.com/feed) | 15 | 2026-09-12 23:01:26 |
| `news_myjoyonline` | MyJoyOnline Ghana | Multimedia Group | en | [RSS](https://www.myjoyonline.com/feed/) | 50 | 2026-09-12 21:27:00 |
| `news_agencia_brasil_en` | Agência Brasil English | Empresa Brasil de Comunicação | en | [RSS](https://agenciabrasil.ebc.com.br/en/rss/ultimasnoticias/feed.xml) | 10 | 2026-09-12 12:00:00 |
| `news_mercopress` | MercoPress | MercoPress | en | [RSS](https://en.mercopress.com/rss) | 10 | 2026-09-12 17:25:00 |
| `news_batimes` | Buenos Aires Times | Editorial Perfil | en | [RSS](https://www.batimes.com.ar/feed) | 100 | 2026-09-12 13:21:18 |
| `news_cna_asia` | CNA Asia | Mediacorp | en | [RSS](https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6511) | 20 | 2026-09-12 22:00:00 |
| `news_japan_times` | The Japan Times | The Japan Times | en | [RSS](https://www.japantimes.co.jp/feed/) | 30 | 2026-09-12 23:05:00 |
| `news_indian_express` | The Indian Express | The Indian Express Group | en | [RSS](https://indianexpress.com/feed/) | 200 | 2026-09-12 22:41:19 |
| `news_hindustan_times` | Hindustan Times India | HT Media | en | [RSS](https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml) | 100 | 2026-09-12 17:33:52 |
| `news_antara_en` | ANTARA News English | ANTARA | en | [RSS](https://en.antaranews.com/rss/news.xml) | 50 | 2026-09-12 22:56:10 |
| `news_bangkok_post` | Bangkok Post | Bangkok Post | en | [RSS](https://www.bangkokpost.com/rss/data/topstories.xml) | 10 | 2026-09-12 22:24:00 |
| `news_abc_australia` | ABC News Australia | Australian Broadcasting Corporation | en | [RSS](https://www.abc.net.au/news/feed/51120/rss.xml) | 25 | 2026-09-12 23:00:33 |
| `news_newsroom_nz` | Newsroom New Zealand | Newsroom | en | [RSS](https://newsroom.co.nz/feed/) | 10 | 2026-09-12 17:00:00 |

Rights and provenance limits:

- Publisher RSS terms remain applicable. Public access does not establish commercial redistribution rights. The Independent and CNA explicitly restrict their RSS to personal, non-commercial use. Headlines are retained; linked article text and imagery are not fetched or stored.
- Reuters-style wires, syndication or shared ownership do not constitute independent corroboration. Declared upstream publisher labels are retained where supplied by the feed.
- BBC feeds share BBC; Reach titles share Reach plc; Newsquest titles share Newsquest; France 24/RFI share France Médias Monde; Euronews/Africanews share Euronews.
- ANTARA and Agência Brasil are labelled state-owned/interested-party. No reliability upgrade is inferred from official ownership, availability or familiar branding.
- New York Times and Japan Times links may require a subscription to read the article. This integration only retains public RSS headline metadata.
- Non-English additions: French RFI, Spanish El País, Portuguese Público and Arabic France 24. Other additions are English. Titles are not machine-translated.
- Missing publication dates remain unknown; no collection date is substituted. All accepted feeds supplied recognised dates during the live check. The Indian Express reached the 200-item parsing cap.

Excluded during bounded discovery:

| Candidate | Observation / reason |
| --- | --- |
| Belfast Telegraph Northern Ireland | HTTP 403 |
| RNZ national / Pacific | HTTP 403 |
| Mail & Guardian | Feed URL HTTP 404 |
| Al-Monitor | HTTP 403 |
| News24 feed host | DNS failure |
| GroundUp | Redirecting www URL; canonical article feed HTTP 404 |
| Fiji Times | Redirecting www URL; canonical feed timed out |
| Kyiv Independent | Feed URL HTTP 404 |
| NHK domestic Japanese feed | Latest observed date 8 August 2026, stale; not NHK World English |
| DW Spanish | XML parsed, but none of the 31 entries supplied a recognised publication date |
| Inquirer | Future-dated feed entries; no timezone inference applied |
| allAfrica | Aggregator feed worked, deferred to avoid treating upstream outlets as a new independent publisher |

Selected primary source directories / terms:

- [Sky RSS directory](https://news.sky.com/info/rss)
- [BBC UK RSS directory](https://support.bbc.co.uk/platform/feeds/UkNews.htm)
- [The Independent RSS terms and directory](https://www.independent.co.uk/service/rss-feeds-775086.html)
- [PBS RSS directory](https://www.pbs.org/newshour/about/pbs-news-rss-feeds)
- [CNA RSS directory](https://www.channelnewsasia.com/rss) and [terms](https://www.channelnewsasia.com/rss/rssterms)
- [Reach brands](https://www.reachplc.com/about-us/our-brands)
- [Newsquest brands](https://www.newsquest.co.uk/our-brands/)
- [Euronews](https://www.euronews.com/about) and [Africanews](https://www.africanews.com/page/about/)

Validation: 139 focused tests passed across test_news_sources.py, test_rss.py, test_publisher_research.py and test_cyber_sources.py. Ruff and mypy passed on the changed feed modules and test file (mypy on source files). No full suite or coverage measurement was run for this additive feed work.

Research capacity repair verified alongside the feed expansion:

The preceding CTI milestone exposed an existing use of 64 for both source inventory metadata and collection work. On isolated HEAD, three source-audit tests reproduced failures: eight-language domain research exceeded the provider cap, saved company research with eight explicit tasks exceeded the expanded-plan cap, and catalogue pruning removed unsupported regional rows from the preview.

The repaired policy centralises capacities in `domain/research_capacity.py`: 128 uniquely identified catalogue providers, 136 frozen plan/coverage receipt rows, 64 explicitly selected sources, eight explicit/model tasks, eight candidate hypotheses and 64 retained input receipts. Retained input receipts share the 136-row total with selected collection tasks. Public collection allowances remain quick 6 requests/200 items, detailed 24/800 and advanced 32/1,000, with unchanged deadlines, pacing and concurrency. Unsupported and budget-exhausted rows are metadata, not extra source requests. No provider is silently dropped to make an inventory fit.

Normal eight-language detailed previews now retain 72 general, 80 company and 78 domain capabilities, including unsupported rows. New broad-news RSS feeds remain retained-feed evidence only; the private publisher set stays 37. No API input limits or generated API schema changed.

Regression evidence: six new capacity tests failed before the implementation; 195 focused research tests passed after it, including all three original source-audit failures. A final 27-test run of capacity/model-planning tests passed after adding a further explicit-source scope assertion. The regression set covers 128-provider admission, 129-provider rejection, 136-task/receipt persistence round trips, 137-row rejection, 64 selected sources plus eight tasks, model task allowance and retained-input receipt reservation, unchanged actual request/item ceilings, unsupported rows, replanning, challenges, report receipt round trips and legacy JSON. Ruff passed for the touched modules/tests, strict mypy passed on 11 source files, and git diff --check passed. No full suite or coverage measurement was run for this scoped repair.
