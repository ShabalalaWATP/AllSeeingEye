# Translation, social monitoring and semantic search

This is the maintained guide for these three capabilities. The historical
filename is retained for existing links; it is no longer a general Phase 5/6
upgrade or security guide. Budgets below describe the current implementation,
not a measured guarantee of provider coverage or model quality.

| Capability | Current guide |
| --- | --- |
| Translation, social sampling, watchlists and semantic search | This page |
| Telegram collection and source restrictions | [Telegram coverage](TELEGRAM_CHANNEL_COVERAGE.md) and [social coverage](SOCIAL_SOURCE_COVERAGE.md) |
| Account MFA, recovery codes and host recovery | [MFA operations](MFA_OPERATIONS.md) |
| Export formats and current PDF font support | [Reporting and assessment](03_DOCTRINE_AND_REPORTING.md) |
| Optional isolated complex-script PDF rendering | [Isolated renderer](ISOLATED_REPORT_RENDERER.md) |
| Model connections and transport deadlines | [AI connection operations](AI_CONNECTIONS_OPERATIONS.md) |
| Installation, migrations and backups | [Setup](SETUP.md) and [backup and restore](BACKUP_RESTORE.md) |
| Team authority and consent | [Team API](api/TEAMS_API.md) |

## Configuration

Translation and semantic search need their appropriate configured model roles
and a recoverable application encryption key. Public map observation does not.
Feed/background work is controlled by the documented settings in
[Setup](SETUP.md). Disabling archive submission is separate from feed collection.

Run one API process: the live store, queues, rate limits and model admission are
process-local. Multiple worker processes do not share these budgets.

## Language detection and translation

Language detection fills missing source languages. To enable translation, set `ASE_ENCRYPTION_KEY`, then save an enabled profile with the `translation` role under Admin, Models. Its chat endpoint must support the application's JSON-schema response format. It may be a local OpenAI-compatible endpoint; no paid provider or cloud service is required by this feature.

Every 30 seconds the queue considers up to 2,000 recently published events from the last 24 hours, selects up to 20 untranslated titles with a known non-English language and makes at most 60 calls per UTC hour. Repeated language/title pairs share a bounded 5,000-entry cache. It preserves the original title and updates `title_en` only while the corresponding current event still matches; pruning, regrading or changed titles cannot be overwritten with a stale captured event. Open pages receive an `event.upsert` message.

Without a usable translation profile or key, original titles remain and later cycles can resume once configuration is available. A returned failed/empty translation is remembered for that event/title during the bounded queue lifetime, rather than retried continuously. Model usage is recorded with purpose `translation`, without persisting provider response bodies as errors. The ticker and relevant event rows prefer the English display title when one exists; grading and frozen source meaning remain separate concerns.

Translation and report generation have scripted-gateway tests. These tests do not establish translation quality, endpoint schema compatibility or real token usage. Verify those against the installation's configured model.

## Social listening and Google News watchlists

Open Trackers, Social at `/trackers/social`. Refresh reloads the retained day's platform/instance totals, located counts, top hashtags and latest 50 posts. The globe button enables the existing social category and selects a 24-hour window. Only events carrying a location appear on the globe. Current Mastodon and YouTube sources usually provide none.

The packaged `backend/src/ase/resources/social_watch.json` contains Mastodon instances and tags. YouTube channels are listed separately in `backend/src/ase/resources/feeds/youtube_channels.json` and are collected only when `ASE_YOUTUBE_API_KEY` is set; with no key they report the missing setting and nothing is polled. Public social posts start at E6; outlet videos retain the outlet's reliability. Reddit was retired on 16 September 2026 because `robots.txt` disallows every path. Bluesky remains deferred in the maintained source policy. Curated public Telegram channels are collected through the bounded preview adapter described in [Telegram coverage](TELEGRAM_CHANNEL_COVERAGE.md); that does not permit arbitrary page scraping.

The social sampler runs every five minutes. It counts matching posts once per keyword in the previous complete UTC hour. Up to 32 normalised terms, selected from the packaged watchlist then enabled collection-plan terms, receive tiny durable samples. Stored keys are digests; rows contain counts, not raw titles, hashtags or posts. Social rows older than 30 days and removed keys are pruned. Zero counts are sampled; hours missed while stopped remain unknown. The board includes personal plan terms only for their owner or an administrator, and team terms for current members or administrators. Background terms require an active owner with current membership of an active originating team. Lists are filtered before their collection limits.

A burst needs at least six earlier sampled hours, at least three posts and a count at least twice the mean. An established zero mean can therefore produce a "new activity" burst. A blank or building baseline is not evidence of inactivity. Counts describe the selected retained feeds, not the whole platform, and a burst is not verification of a claim.

Enabled collection plans also supply Google News RSS keyword searches. The collector selects at most 12 deduplicated literal phrases, up to 60 characters each, sends at most one request per minute and 48 per rolling hour, and waits at least 15 minutes before reusing a term. The configured phrase is sent to Google. The current edition is GB English with `when:1d`; there is no article scraping or bulk history import. Source health is shown under `google_news_watchlists`. Errors do not expose private plan terms in shared source health.

Only cited evidence enters Google URL resolution, capped at 30 unique URLs and ten seconds per report. Older envelopes that directly embed the publisher URL can be decoded and checked for a public destination. Failed, malformed, private-address, uncited and modern opaque links retain the original URL. A signature-free modern `batchexecute` probe returned null with status 3 on 6 September 2026. The implementation does not obtain signatures by fetching article HTML. Decoding a publisher URL alone does not establish publisher independence or change its grade.

## Semantic search of saved reports

Under Admin, Models, enable a profile with the `embeddings` role and an endpoint implementing `/embeddings`. On Reports, "Find related reports" shows availability and index coverage. Choose "Index next 8 reports" explicitly until the wanted current reports are indexed. Opening the page does not send report text to the model.

The caller's newest 1,000 visible saved reports are eligible. Storage has a shared limit of 1,000 vectors, checked before embedding new rows. A full index returns an explicit capacity error without calling the model; existing vectors remain searchable. This operation never evicts another scope's current vectors. Each has at most one vector for its current version and model fingerprint; only matching entries participate in queries. A changed report or different profile/model requires indexing again. The input is the report title and structured body, capped at 6,000 characters per report; live events are never embedded. Search text is limited to 500 characters and results to 20. A normal query requests ten results.

Vectors contain at most 4,096 finite numeric dimensions and are normalised before storage/comparison. They are stored as bounded JSON in `report_embeddings` for SQLite/PostgreSQL portability. There is no vector database service or pgvector dependency. Global housekeeping removes deleted or superseded versions. Cosine similarity runs locally over the caller's currently visible records. Similarity ranks related wording and meaning; it is not a source grade, probability or confidence rating.

Embedding calls share a single in-process lock and are capped at 30 per user/hour and 60 globally/hour. Indexing is one call per batch; a query needs one embedding call only when usable indexed reports exist. Usage rows use purpose `embeddings`. Report existence, version and current account/team access are rechecked after model calls. Real embedding quality and endpoint compatibility remain unverified until a model is configured and exercised.

## Source and validation references

Translation budgets and stale-event checks live in
[the translation queue](../backend/src/ase/application/translate/queue.py).
Social sampling is implemented by
[SocialMonitor](../backend/src/ase/application/trackers/social.py).
Search capacity and current visibility are enforced by
[ReportSearchService](../backend/src/ase/application/reports/search.py) and its
persistence adapter. These source checks were made on 30 September 2026.

Offline tests do not establish live provider availability, research quality,
24-hour translation performance or export layout in a particular viewer.
