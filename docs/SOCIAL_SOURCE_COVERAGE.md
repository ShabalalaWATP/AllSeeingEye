# Social source verification, 16 September 2026

The task was to widen Mastodon, Reddit and YouTube coverage across the full topic
spread. Mastodon was widened. Reddit and YouTube were not, because both hosts'
`robots.txt` disallow the exact paths this application polls. This page records every
check, what was added, and what was refused.

**Follow-up the same day.** The nine feeds that were already being polled on those
disallowed paths have now been retired, and YouTube coverage has been rebuilt on the
official Data API v3. [What was done](#what-was-done-16-september-2026) records that
decision, its quota arithmetic and the Reddit position.

## Method

Every candidate was fetched from this machine with the application's polite
`User-Agent`. `robots.txt` was read and evaluated with Python's `urllib.robotparser`
against the exact path the connector would request, which is the same method
[NEWS_SOURCE_COVERAGE.md](NEWS_SOURCE_COVERAGE.md) used to reject Civil Georgia. The
Mastodon candidates that passed were then fetched a second time through the
application's own `FeedHttpClient` and `MastodonConnector`, so the recorded counts are
events this application actually produced, not an ad hoc script's.

## Reddit: not widened

`robots.txt` on `www.reddit.com`, `old.reddit.com` and `oauth.reddit.com` is, in full
for every user agent:

```
User-agent: *
Disallow: /
```

`robotparser` returns `False` for `/r/worldnews/new/.rss` and for every other subreddit
listing. Reddit's own robots file points at its Public Content Policy, which directs
programmatic access to the Data API with a registered OAuth application. There is no
unauthenticated path that robots permits, so no subreddit was added.

This applies equally to the three subreddits already in the catalogue
(`reddit_worldnews`, `reddit_geopolitics`, `reddit_ukrainianconflict`). They were not
removed here: that is an operator decision, and each has a research provider and a
reviewed allocation profile behind it. It should be taken. `06_OPEN_QUESTIONS.md`
already records the OAuth registration (100 requests per minute) as the intended route.
**That decision was taken later the same day and all three were removed**; see below.

What was left unadded, had robots permitted it: CredibleDefense, LessCredibleDefence,
OSINT, netsec, cybersecurity, blueteamsec, Economics, geopolitics-adjacent regional
subreddits, drone and UAS subreddits.

## YouTube: not widened

`robots.txt` on `www.youtube.com` contains, under `User-agent: *`:

```
Disallow: /feeds/videos.xml
```

That is the exact path a channel feed uses
(`/feeds/videos.xml?channel_id=...`), so `robotparser` returns `False` for every
channel including the six already carried. YouTube's terms point at robots.txt for
automated access and at the Data API otherwise, so no handle was resolved to a channel
ID and no channel was added. **The six existing channel feeds were removed later the
same day and rebuilt on the Data API**; see below.

The compliant route is the YouTube Data API v3: one `playlistItems.list` call against a
channel's uploads playlist costs 1 unit against a 10,000 unit daily quota, so 40
channels polled every 30 minutes would spend about 1,920 units a day. That needs a key
and a keyed connector on the existing "keyed sources join only when their key exists"
pattern in `adapters/feeds/registry.py`. It was not built here because it cannot be
verified live without the key.

## Mastodon: widened from one instance and seven hashtags to four and sixteen

`robots.txt` on every Mastodon instance checked disallows only `/media_proxy/`,
`/interact/` and `/api/v1/instance/domain_blocks`; `robotparser` returns `True` for
`/api/v1/timelines/tag/<tag>`. Public tag timelines need no key and no account, and the
connector never authenticates.

### Carried

Each row was fetched through `MastodonConnector` on 16 September 2026. "Posts" is the
number of events the connector produced from one full poll of that instance's tags.

| Instance | Active users/month | Tags | Poll | Requests/poll | Posts | Newest post | Median post age |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `mastodon.social` | 267,552 | 12 | 15 min | 12 | 455 | 1 min | 2.3 h |
| `defcon.social` | 2,291 | 8 | 20 min | 8 | 285 | 1 min | 2.7 h |
| `journa.host` | 248 | 8 | 20 min | 8 | 300 | 2 min | 4.4 h |
| `eupolicy.social` | 188 | 6 | 30 min | 6 | 225 | 2 min | 3.9 h |

Every post arrived at reliability E and credibility CANNOT_BE_JUDGED with subtype
`post`, which is doctrine's floor, unchanged. Returned languages included Arabic,
Catalan, Dutch, English, French, German, Indonesian, Italian, Spanish and Ukrainian.

Instances were chosen for distinct communities rather than volume. A tag timeline is
mostly federated content, so instances overlap: measured against `mastodon.social` over
the same four tags, `defcon.social` carried 35 per cent of posts that `mastodon.social`
did not, `journa.host` 76 per cent and `eupolicy.social` 79 per cent. Those percentages
are an upper bound, because a smaller instance sees less of the firehose and so its
timeline reaches further back for the same request. The duplicate share is the reason
the instance list stays at four: the same post on two instances becomes two events,
because both the instance-local status ID and the source ID differ.

- `mastodon.social` is the broadest general-purpose reach.
- `defcon.social` is the security-research community, and replaces `infosec.exchange`
  for cyber coverage (see below).
- `journa.host` is journalists and newsrooms; membership is closed, which is a quality
  signal rather than a problem for reading.
- `eupolicy.social` is the EU policy community, which is where sanctions, energy and
  Ukraine policy material appears.

### Hashtags

Sixteen distinct: `breakingnews`, `china`, `cybersecurity`, `drones`, `earthquake`,
`gaza`, `geopolitics`, `infosec`, `iran`, `osint`, `russia`, `sanctions`, `sudan`,
`taiwan`, `threatintel`, `ukraine`. The seven already packaged are all retained.

The set stops at sixteen for a reason that is not visible from the data. The packaged
tags are the public half of the social board's watched vocabulary, and
`ase.domain.social.MAX_TERMS` caps that vocabulary at 32 with the packaged tags taking
their slots first. Every extra packaged tag is one fewer slot for an operator's own
collection terms, so the packaged set is held to half the cap. `korea`, `maritime`,
`aviation`, `space`, `energy`, `nato`, `natsec`, `disinformation`, `sahel`,
`venezuela`, `syria`, `africa`, `india`, `israel`, `ransomware` and `uav` all returned
recent posts when probed and were left out only for this reason. Raising
`MAX_DISTINCT_TAGS` in `adapters/feeds/mastodon_watch.py` is a product decision about
that shared cap, not a source decision.

### Refused

| Candidate | Why |
| --- | --- |
| `infosec.exchange` | `422 {"error":"This method requires an authenticated user"}` on every tag; the instance has disabled unauthenticated API access |
| `ioc.exchange` | Same 422 |
| `respublicae.eu` | Same 422 |
| `social.network.europa.eu` | Does not resolve from this host |
| `mstdn.social`, `mas.to`, `masto.ai`, `hachyderm.io`, `techhub.social`, `flipboard.social`, `newsie.social` | All answered correctly, but each duplicates `mastodon.social` too heavily (22 to 47 per cent new content) to pay for its own requests in a bounded store |

## Polling load

Mastodon goes from 42 requests an hour (7 tags every 10 minutes on one instance) to 108
(48 + 24 + 24 + 12). Reddit and YouTube were 8 and 12 requests an hour before the
retirement recorded below. Reddit is now zero, and YouTube is 58 an hour on the keyed
API route.

Every watched instance is now spaced by the shared per-host pacer at one second between
request starts, and `www.googleapis.com` likewise, so a restart cannot burst either
upstream. The scheduler's existing `Retry-After` backoff is untouched: the Mastodon
connector propagates a rate limit rather than swallowing it, and only skips a tag the
instance answers 404 or 410 for.

## Research catalogue

No research provider was added for Mastodon. New Mastodon sources feed the live layer
only. The nine `research_social_*` providers were later removed with their feeds and one
aggregated `research-youtube` provider was added; see below.

The six broadcaster YouTube channels and three subreddits each had a
`research_social_<id>` provider because every entry in `SOCIAL_SEEDS` derived one, and
`MAX_COLLECTION_PROVIDERS` caps the catalogue at 160 with 138 in use. Nothing was added
to `SOCIAL_SEEDS`, so the count was unchanged and no allocation profile needed review.

An aggregated provider per platform was considered and rejected on its own merits, not
only for the count: a research provider fetches live at question time, so one covering
sixteen Mastodon tag timelines would fan out sixteen requests per research task against
the same volunteer instances the scheduler already polls. The live layer is the right
place for this material, and the social board already exposes it.


## What was done, 16 September 2026

Both robots files were fetched again with `curl` before anything changed, and both said
exactly what the checks above recorded.

`https://www.reddit.com/robots.txt`, in full apart from its comments:

```
User-agent: *
Disallow: /
```

The comments point at Reddit's Public Content Policy for access and use restrictions,
and at `r/reddit4researchers` for research use.

`https://www.youtube.com/robots.txt`, under `User-agent: *`, lists among others:

```
Disallow: /feeds/videos.xml
```

That is the exact path a channel Atom feed uses.

### The nine non-compliant feeds were retired

Removed from the scheduled catalogue: `reddit_worldnews`, `reddit_geopolitics`,
`reddit_ukrainianconflict`, `yt_bbc_news`, `yt_reuters`, `yt_dw_news`, `yt_al_jazeera`,
`yt_france24` and `yt_sky_news`. With them went the whole `research_social_*` provider
family and its nine reviewed allocation profiles, the `SocialFeedResearchProvider`
adapter, the `research_social_` control prefix, the `www.reddit.com` entry in the shared
host pacer, and `reddit` from the social board's platform list. The executable E00
research catalogue fell from 138 routes to 129.

This is not a judgement that the material was worthless. It is that this project's own
rules say to respect source terms, and a path the host disallows is not one this
application may poll, however useful its contents.

### YouTube was rebuilt on the Data API v3

A keyed connector now reads twenty-nine reviewed channels. It follows the existing
"a keyed source joins only when its credential exists" pattern: with no
`ASE_YOUTUBE_API_KEY` no connector is constructed, every YouTube source reports the
missing setting exactly as ACLED and Companies House do, and nothing is collected. There
is no public fallback, because the only public path is the one robots disallows.

The call pattern is the cheapest the API allows:

| Call | Units | When |
| --- | ---: | --- |
| `channels.list` (handle or ID to uploads playlist) | 1 | Once per channel per process start |
| `playlistItems.list` (latest 25 uploads) | 1 | Every poll, per channel |
| `search.list` (on-demand video research) | 100 | Per research task that selects the route |

Against the default quota of 10,000 units a day:

- 29 channels times 48 polls a day (one every 30 minutes) is **1,392 units**, about 14
  per cent of the quota.
- Resolution adds **29 units** per restart, not per day.
- On-demand research is capped locally at **40 searches a day, 4,000 units**, so the
  worst day is about **5,421 units**, roughly 54 per cent. The cap exists so a busy
  research day cannot starve scheduled collection.
- `search.list` was deliberately not used for channel polling. Polling 29 channels with
  it would cost 139,200 units a day, fourteen times the whole quota.

What is collected: video title, publication time (`contentDetails.videoPublishedAt`, not
playlist insertion time), channel identity, the `watch?v=` link and a description excerpt
bounded to 500 characters. No transcripts, caption tracks, comments, thumbnails or media
are fetched.

Grades follow the existing rules. Outlet channels keep their outlet's reliability;
official bodies' own channels are graded B with credibility 2, as their other official
publications are; independent analysis channels sit at doctrine's floor, E with
credibility 6, and take an explicitly unassessed rating rather than an inherited
editorial grade; CGTN is tagged `state_controlled` with credibility 4.

Channels, by topic: world reporting (BBC, Reuters, AP, DW, France 24, Sky, Guardian,
euronews, PBS NewsHour); Ukraine and Russia (Kyiv Independent, Meduza); China and Taiwan
(SCMP, TaiwanPlus, CGTN); Middle East (Al Jazeera English, Middle East Eye); finance
(CNBC, Financial Times, The Economist); cyber (DEF CON, Black Hat); defence analysis and
drones (Perun, War on the Rocks, Chatham House); official channels (NATO, The White
House, 10 Downing Street, the United Nations, the European Commission). The six
broadcasters the retired feeds carried are all among them.

One aggregated research provider was added, `research-youtube`, with a reviewed
allocation profile. It is one platform-wide `search.list` call per research task, not a
fan-out across channels, and it returns the executable catalogue to 130 routes. It is the
reason the daily search allowance exists.

### What is unverified

No key exists on this machine, so **nothing here has been run against the live API**. The
connector and the research provider are proved against fixtures in
`backend/tests/fixtures/feeds/youtube_*.json`, which carry the documented response shapes
rather than captured live responses. In particular, the twenty-three channel handles that
carry no channel ID were reviewed offline and have not been confirmed to resolve. A
handle that does not resolve costs one quota unit, fails that one channel's poll with an
explicit error, and shows in source health; it never affects another channel. The first
run with a key should be checked for exactly that.

### Reddit: the compliant route, and what the operator would have to do

There is no compliant unauthenticated route. Reddit's robots file disallows every path
for every user agent and points at the Public Content Policy, which directs programmatic
access to the authenticated Data API. Using it would need:

1. A Reddit account with two-factor authentication, then an app registration at
   `https://www.reddit.com/prefs/apps` of type "script", giving a client ID and secret.
2. Agreement to the Reddit Data API Terms and the Public Content Policy in the operator's
   own name, including their non-commercial and rate conditions. The free tier is 100
   queries per minute per OAuth client ID.
3. A descriptive `User-Agent` in Reddit's required format, and OAuth2 client-credentials
   token handling against `https://www.reddit.com/api/v1/access_token`, reading
   `https://oauth.reddit.com/r/<sub>/new`.
4. Two settings on this server (client ID and secret) and a keyed connector on the same
   pattern the YouTube one now uses.

That has **not** been built. It is a live decision for the operator, not something to
assume on their behalf.
