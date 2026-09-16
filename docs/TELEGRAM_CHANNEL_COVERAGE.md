# Curated Telegram channel coverage, 16 September 2026

Telegram is where most Ukraine and Russia war material appears first, and the operator
asked for it explicitly after the trade-off was explained. This reverses open question 7,
which recommended leaving Telegram out of the first release and adding the preview-page
connector later "as an opt-in with a clear warning". This document is that warning.

## What is collected, and what is not

Telegram publishes no read API for public channels without an account. The Bot API cannot
read a channel it does not administer, and an MTProto client would need a personal account
and carry ban and terms-of-service risk. The remaining route is the public channel web
preview at `https://t.me/s/<channel>`, which needs no account.

The connector requests that one page per channel and nothing else. It never fetches media,
never follows a link found inside a post, never requests a post permalink, and never reads
anything that requires signing in. What it keeps is a plain-text excerpt of at most 700
characters, the post time, the view count and the post's own permalink.

## robots.txt and terms

Checked on 16 September 2026:

- `https://t.me/robots.txt` answers **HTTP 404**.
- `https://telegram.org/robots.txt` answers **HTTP 404**.
- `https://t.me/s/DeepStateUA` answers HTTP 200 with no `X-Robots-Tag` response header.

No crawl rules are published at either host, so none are being ignored. Under RFC 9309 an
unavailable `robots.txt` leaves access unrestricted. That is permission by absence, not
endorsement, so the connector behaves as though a strict rule existed: one page per
channel, a shared five-second gap between requests to `t.me`, poll intervals of 30 to 240
minutes, and a stop rather than a retry loop when Telegram refuses. Telegram's preview
pages send `Cache-control: no-store` and no validator, so conditional requests do not help
and every poll is a full page fetch of roughly 200 KB.

## How the parser fails safe

HTML parsing is something this application otherwise avoids, so the parser
(`adapters/feeds/telegram_preview.py`) is written to refuse rather than improvise:

| Situation | Result |
| --- | --- |
| Page larger than 1,500,000 characters | Refused before parsing |
| Markup nested deeper than 200 elements | Refused |
| No `tgme_channel_history` section (private, removed, not a channel, preview off) | Refused, with that list as the stated reason |
| History present but no post the parser can read | Refused as a probable markup change |
| History present but the posts belong to another channel | Refused as a probable markup change |
| A post with no usable timestamp | Kept, with no publication date invented |
| A post with an unusable identifier, or no text | Dropped |
| More than 20 posts, or an excerpt over 700 characters | Truncated to the cap |

Every refusal raises `TelegramMarkupError`, which the connector turns into `FeedBlocked`
with fixed operator-facing text and a six-hour recheck. That is the same mechanism the
CISA and ACSC advisory feeds use, so the interface says why a channel is idle. A markup
change therefore shows as "provider unavailable", never as a channel that has gone quiet
and never as a wrong post. HTTP 401, 403, 404, 410 and 451 defer the same way with a
twelve-hour recheck; HTTP 429 is left to the scheduler's existing `Retry-After` backoff.

## Grading and labelling

Every post from every channel is collected at doctrine's floor: reliability E and
credibility 6 (`CANNOT_BE_JUDGED`) in the live layer, reliability F in the research route.
No channel receives an uplift, including the official ones. The registry records a
viewpoint instead, which maps onto the tag vocabulary the state-aligned news feeds already
use, so the interface marks these channels exactly as it marks those feeds:

| Viewpoint | Meaning | Tags |
| --- | --- | --- |
| `official_issuer` | An institution's own account, speaking for that institution | `official_issuer`, `interested_party` |
| `state_media` | A state-run, state-funded or state-directed outlet | `state_aligned`, `interested_party` |
| `aligned_commentator` | Openly aligned with one party: milbloggers, advocacy, mapping | `interested_party` |
| `publisher` | An outlet or researcher with no declared party alignment | none |

Russian and Ukrainian military channels are participants, not observers, and are graded as
such. A ministry of defence is authoritative only about what it chose to say. The registry
also records who operates each channel, because several channels carry official-sounding
names and are run by nobody in particular; `operativnoZSU` is exactly the case the
`operator` field exists to disambiguate.

## Content hazard

These channels carry graphic imagery, casualty footage, prisoner-of-war material and
unverified claims, and some of them publish deliberate falsehoods. Three mitigations:

1. **No media is ever fetched or stored.** Text excerpts and links only, so graphic images
   and video never enter the store, the reports or the interface.
2. **Links are not followed.** A URL inside a post contributes its anchor text and nothing
   else; the target is never requested and never resolved.
3. **Nothing is rendered as HTML.** Text is reduced to plain text at parse time.

A reader who follows a post permalink leaves the application and will see the original
media. That is a deliberate boundary, not an oversight.

## The registry

63 channels, all fetched and parsed with the application's own parser on 16 September 2026
and all with a post inside the previous 16 days. Grouped by topic:

| Topic | Count | Examples |
| --- | ---: | --- |
| `ukraine_official` | 5 | Office of the President, General Staff, Air Force Command, MVS, Ukrenergo |
| `ukraine_media` | 9 | Ukrinform, Suspilne, Ukrainska Pravda, The Kyiv Independent, NEXTA |
| `russia_official` | 4 | Russian MoD (Russian and English), Russian MFA (Russian and English) |
| `russia_state_media` | 4 | TASS, RIA Novosti, Izvestia, Readovka |
| `russia_milblogger` | 11 | Rybar, Colonelcassad, WarGonzo, Poddubny, Dva Majora, Intel Slava Z |
| `russia_independent` | 9 | Meduza, Mediazona, ASTRA, Agentstvo, Baza, SHOT, RBC, Kommersant |
| `conflict_monitoring` | 5 | DeepState, Gerashchenko, Tsaplienko, Operatyvno ZSU, OSINTdefender |
| `middle_east` | 5 | IDF, Israel War Room, Quds News Network, Press TV, IRNA |
| `cyber_threat` | 4 | vx-underground, The Hacker News, BleepingComputer, RedPacket Security |
| `finance_sanctions` | 3 | Bank of Russia, National Bank of Ukraine, Bloomberg |
| `emergency_response` | 2 | DSNS Ukraine, EMERCOM Russia |
| `asia_pacific` | 1 | South China Morning Post |
| `africa_sahel` | 1 | Mali Actu |

The full list, with the operator and the one-line reason for each entry, is in
`backend/src/ase/adapters/feeds/telegram_channels_{ukraine,russia,correspondents,world}.py`.

## What was rejected, and why

229 candidate channels were probed across four rounds and 63 were kept. The failure modes:

- **No public preview.** The `@name` resolves but `t.me/s/<name>` serves the generic
  contact page with no channel history: `ssu_telegram`, `butusov_plus`, `hromadskeua`,
  `KyivPost`, `RT_com`, `rt_russian`, `SputnikInt`, `themoscowtimes`, `novayagazeta`,
  `theins_ru`, `IranIntl`, `MiddleEastEye`, `AlMayadeenNews`, `ChinaDaily`, `PeoplesDaily`,
  `CGTNOfficial`, `XinhuaNews`, `globaltimesnews`, `TaiwanPlusNews`, `nknews`,
  `saharareporters`, `sudanwarmonitor`, `africanews_en`, `FinancialTimes`, `visegrad24`,
  and every drone-specific candidate tried.
- **Dormant.** A preview that parses but whose newest post is months or years old:
  `ukrainenowenglish` (2022), `osinttechnical` (2022), `almayadeen_news` (2022),
  `sepahnews` (2023), `iranintl_en` (2023), `cyberwar_ua` (2023), `bellingcat` (2024),
  `grey_zone` (2025), `timesofisrael` (2025), `AfricaNews` (2025), `sudantribune` (2025),
  `nytimes` (2026-03), `aljazeeraenglish` (2026-02), `ReutersWorldChannel` (2026-07).
- **Not what the name implies.** `ZelenskyyOfficial` is a channel called "Robert" with one
  post from 2023; `ZN_UA` is a dating channel; `KoreaHerald` is a Russian-language reposter
  with a stylised title; `taiwannews` is an unrelated channel. These are the reason the
  registry carries an `operator` field and why every entry was opened before it was added.
- **Operator not establishable.** Active and useful, but the account behind it could not be
  established well enough to describe honestly: `war_monitor`, `air_alert_ua`, `bbbreaking`,
  `warmonitors`, `insiderUKR`, `russica2`, `palestineonline`, `Cyber_Security_Channel`,
  `if_market_news`. `operativnoZSU` and `UkraineNow` were kept as exceptions, both labelled
  explicitly as unattributed Ukrainian war-news channels rather than the official or
  government channels their names suggest, because that confusion is itself worth surfacing.
- **Mislabelled during review, caught before release.** `minfin_news` was first entered as
  the Ukrainian finance portal minfin.com.ua. Its own channel description says it
  republishes Russian Ministry of Finance and Federal Tax Service material, so it was
  dropped. Every registry claim was cross-checked against the channel's own description for
  exactly this reason.

## Known gaps

No Chinese state channel, Taiwanese outlet, Korean outlet or dedicated drone or uncrewed
systems channel could be verified: the obvious candidates publish no channel preview.
China and Taiwan rest on one outlet (SCMP) and Africa on one (Mali Actu). Latin America,
South Asia and Central Asia have no entry at all. These are gaps in what Telegram exposes
publicly, not oversights, and the RSS catalogue already covers several of them.

## Load

63 channels at 30 to 240 minute intervals is about 57 requests an hour to `t.me`, roughly
one a minute, spaced at five seconds by the shared per-host pacer. At around 200 KB per
uncacheable page that is roughly 11 MB an hour.

## Research

The whole curated set is a **single** research provider, `research_social_telegram`, not
one per channel: the research catalogue is bounded by `MAX_COLLECTION_PROVIDERS` and one
provider per channel would exhaust it. The provider port allows one HTTP request per
collection, so a collection reads exactly one channel preview, selected deterministically
by declared language and subject overlap with the supplied phrases. That limit is stated in
the capability constraints, the catalogue limitations and every collection receipt: it is
not a Telegram search, a channel archive or a sweep of the curated set.
