# Phase 5 and Phase 6 operations

Updated 6 September 2026. This guide describes the implemented local application, its fixed budgets and the checks that still need the operator's environment. See the [feature inventory](04_FEATURES_AND_VIEWS.md), [source probes](02_DATA_SOURCES.md#o-live-verification-5-september-2026), [backup guide](BACKUP_RESTORE.md) and [ASVS review](security/PHASE6_ASVS_REVIEW.md).

## Upgrade and configuration

Preserve a verified durable database backup and the existing `ASE_ENCRYPTION_KEY` before upgrading. From `C:\AlexDev\OSINT\backend`, `uv run ase migrate` applies the current Alembic head. Migration `0009` adds encrypted administrator TOTP state and replay tracking; `0010` adds one bounded report-embedding row per indexed report; `0011` adds durable `refresh_family_revocations` markers so revoked families cannot produce usable refresh descendants through concurrent rotation. Social baselines reuse `activity_samples` from `0005`; translation and watchlists create no raw-event tables.

The settings below already exist. The numerical feature budgets in this guide are code constants, not additional environment switches.

| Setting | Operational effect |
|---|---|
| `ASE_ENCRYPTION_KEY` | Needed to save/decrypt model credentials and enrol/decrypt TOTP secrets. Retain the same key with recovery records; losing it makes encrypted state unreadable |
| `ASE_FEEDS_ENABLED` | Starts the collectors and background monitors, including translation and social sampling. Defaults to enabled outside tests |
| `ASE_FEEDS_DISABLED` | Comma-separated source IDs to omit. Include `google_news_watchlists` to stop Google keyword collection while retaining other feeds |
| `ASE_FEEDS_CONTACT` | Contact address in the descriptive feed User-Agent |
| `ASE_ARCHIVE_ENABLED` | Controls optional Wayback submission of cited URLs, independently of Google URL resolution |
| `ASE_LIVE_STORE_MEMORY_MB` | Estimated live-store memory budget, default 512 MiB. This is not a hard process-memory ceiling |

Run one API process. The event store, queues, rate limits, model admission, search lock and rendering slots are process-local. Multiple workers would duplicate collection and budgets rather than sharing them.

## Language detection and translation

Language detection fills missing source languages. To enable translation, set `ASE_ENCRYPTION_KEY`, then save an enabled profile with the `translation` role under Admin, Models. Its chat endpoint must support the application's JSON-schema response format. It may be a local OpenAI-compatible endpoint; no paid provider or cloud service is required by this feature.

Every 30 seconds the queue considers up to 2,000 recently published events from the last 24 hours, selects up to 20 untranslated titles with a known non-English language and makes at most 60 calls per UTC hour. Repeated language/title pairs share a bounded 5,000-entry cache. It preserves the original title and updates `title_en` only while the corresponding current event still matches; pruning, regrading or changed titles cannot be overwritten with a stale captured event. Open pages receive an `event.upsert` message.

Without a usable translation profile or key, original titles remain and later cycles can resume once configuration is available. A returned failed/empty translation is remembered for that event/title during the bounded queue lifetime, rather than retried continuously. Model usage is recorded with purpose `translation`, without persisting provider response bodies as errors. The ticker and relevant event rows prefer the English display title when one exists; grading and frozen source meaning remain separate concerns.

Translation and report generation have scripted-gateway tests. A real configured model has not been exercised on this host, so translation quality, endpoint schema compatibility and real token usage still require a local smoke test.

## Social listening and Google News watchlists

Open Trackers, Social at `/trackers/social`. Refresh reloads the retained day's platform/instance totals, located counts, top hashtags and latest 50 posts. The globe button enables the existing social category and selects a 24-hour window. Only events carrying a location appear on the globe. Current Mastodon, Reddit and YouTube feeds usually provide none.

The packaged `backend/src/ase/resources/social_watch.json` contains Mastodon instances and tags. Reddit and outlet YouTube feeds are seeded separately. Public social posts start at E6; outlet videos retain the outlet's reliability. Bluesky is deferred after 403 responses from this host; Telegram and page scraping remain excluded.

The social sampler runs every five minutes. It counts matching posts once per keyword in the previous complete UTC hour. Up to 32 normalised terms, selected from the packaged watchlist then enabled collection-plan terms, receive tiny durable samples. Stored keys are digests; rows contain counts, not raw titles, hashtags or posts. Social rows older than 30 days and removed keys are pruned. Zero counts are sampled; hours missed while stopped remain unknown. The board includes personal plan terms only for their owner or an administrator, and team terms for current members or administrators. Background terms require an active owner with current membership of an active originating team. Lists are filtered before their collection limits.

A burst needs at least six earlier sampled hours, at least three posts and a count at least twice the mean. An established zero mean can therefore produce a "new activity" burst. A blank or building baseline is not evidence of inactivity. Counts describe the selected retained feeds, not the whole platform, and a burst is not verification of a claim.

Enabled collection plans also supply Google News RSS keyword searches. The collector selects at most 12 deduplicated literal phrases, up to 60 characters each, sends at most one request per minute and 48 per rolling hour, and waits at least 15 minutes before reusing a term. The configured phrase is sent to Google. The current edition is GB English with `when:1d`; there is no article scraping or bulk history import. Source health is shown under `google_news_watchlists`. Errors do not expose private plan terms in shared source health.

Only cited evidence enters Google URL resolution, capped at 30 unique URLs and ten seconds per report. Older envelopes that directly embed the publisher URL can be decoded and checked for a public destination. Failed, malformed, private-address, uncited and modern opaque links retain the original URL. A signature-free modern `batchexecute` probe returned null with status 3 on 6 September 2026. The implementation does not obtain signatures by fetching article HTML. Decoding a publisher URL alone does not establish publisher independence or change its grade.

## Administrator TOTP

Open Admin, Security at `/admin/security` as an active administrator. Enter the current password, add the displayed setup key to a time-based authenticator account and confirm a six-digit code within ten minutes. The key appears only during enrolment and is encrypted at rest. Confirmation consumes that time step; wait for a fresh code before signing in again. The server accepts the current 30-second step and one adjacent step in either direction, with atomic replay protection.

TOTP management is restricted to the administrator's own account and limited to five attempts per minute by user and IP. Sign-in applies the existing login rate limits and lockout rules. Disabling TOTP requires both the current password and an unused authenticator code. Enabling, disabling and local recovery revoke refresh sessions; the UI signs out after management changes. Access tokens carry a refresh-family identifier and account security version. Revoked families and changed account credentials are rejected on the next request; active streams recheck before delivery and at most every 15 seconds while idle. Password reset and role demotion preserve an enrolled TOTP secret. Keep the host and authenticator clocks accurate.

If the authenticator is lost, run this on the host from `C:\AlexDev\OSINT\backend`:

```powershell
uv run ase recover-admin-totp --email your-admin-address@example.com
```

The command prompts privately for the current password and asks for confirmation. It removes the account's TOTP state, revokes refresh sessions and records an audit event. There is no remote recovery endpoint and no recovery-code bundle. Sign in and enrol a new authenticator afterwards. See the ASVS review for access-token revocation and deployment limits.

## Report exports and version comparison

The report reader offers PDF and DOCX downloads for the displayed saved version, alongside Markdown. Exports contain structured report sections, direction/advocacy where present, validation state and a frozen evidence annex with grades, URLs, timestamps and hashes. Versions requiring review or with failed generation retain visible warnings. The renderer treats source text as text and fetches no external images, HTML, fonts or linked documents.

Rendering runs outside the event loop, with two concurrent render slots. Excess jobs are refused with a retry response. Document input is capped at 300,000 characters, 16,000 characters per block, 2,000 blocks and 100 evidence items. The download is generated on demand and is not added to the database.

The PDF uses bundled Bitstream Vera fonts. Unsupported characters are printed as `[U+XXXX]` code points with a note, rather than silently lost. DOCX retains the original valid Unicode. DOCX package structure and content have automated tests, but LibreOffice is unavailable here, so office-renderer visual QA remains outstanding. Inspect a representative multilingual export before depending on its layout outside this host.

Select two saved versions of the same report to compare structured changes. The comparison includes report content, direction, advocacy, validation and frozen evidence. Evidence is matched by event ID so replacing a citation cannot be hidden by reusing its label. Added, removed and changed fields are shown without a model call. Downloads and comparisons use the report reader's access rules; personal reports are visible to their owner and administrators, while team reports are visible to current members and administrators. The same policy controls exports, comparisons and search. Binary exports recheck access after rendering; private API responses use no-store cache headers.

## Semantic search of saved reports

Under Admin, Models, enable a profile with the `embeddings` role and an endpoint implementing `/embeddings`. On Reports, "Find related reports" shows availability and index coverage. Choose "Index next 8 reports" explicitly until the wanted current reports are indexed. Opening the page does not send report text to the model.

The caller's newest 1,000 visible saved reports are eligible. Storage has a shared limit of 1,000 vectors, checked before embedding new rows. A full index returns an explicit capacity error without calling the model; existing vectors remain searchable. This operation never evicts another scope's current vectors. Each has at most one vector for its current version and model fingerprint; only matching entries participate in queries. A changed report or different profile/model requires indexing again. The input is the report title and structured body, capped at 6,000 characters per report; live events are never embedded. Search text is limited to 500 characters and results to 20. A normal query requests ten results.

Vectors contain at most 4,096 finite numeric dimensions and are normalised before storage/comparison. They are stored as bounded JSON in `report_embeddings` for SQLite/PostgreSQL portability. There is no vector database service or pgvector dependency. Global housekeeping removes deleted or superseded versions. Cosine similarity runs locally over the caller's currently visible records. Similarity ranks related wording and meaning; it is not a source grade, probability or confidence rating.

Embedding calls share a single in-process lock and are capped at 30 per user/hour and 60 globally/hour. Indexing is one call per batch; a query needs one embedding call only when usable indexed reports exist. Usage rows use purpose `embeddings`. Report existence, version and current account/team access are rechecked after model calls. Real embedding quality and endpoint compatibility remain unverified until a model is configured and exercised.

## Model transport and deployment checks

Both chat-completion and embedding transports request `Accept-Encoding: identity` and reject compressed responses before reading the body. A provider or reverse proxy that forces gzip/Brotli must be configured to honour identity encoding. Response budgets are 4 MiB for chat and 2 MiB for embeddings; redirects are disabled. Chat has a 120-second total deadline and two concurrent request slots; embeddings have a 30-second transport deadline. Administrator-configured local model endpoints are an intentional trust boundary.

Phase 6 separates MapLibre and deck.gl build chunks, improves live-store pruning and adds a keyboard skip-to-main-content link. These changes and local state tests do not establish measured behaviour under every workload, screen-reader conformance or ASVS level 2 certification. Follow the [security review](security/PHASE6_ASVS_REVIEW.md) before considering exposure beyond the LAN.

Use the [backup and restore guide](BACKUP_RESTORE.md) for verified bundles and restoration to new targets. SQLite recovery was exercised against real temporary WAL data. The actual CLI recovery drill also passed on disposable PostgreSQL 17: all 19 migrated tables matched, including frozen evidence and encrypted credentials, and both recovered secrets decrypted with the preserved test key. This verifies synthetic recovery; repeat it for the operator's backup location and key handling. Backups exclude the live event cache and omit the real `.env` unless the operator explicitly selects plaintext secret inclusion. Preserve the matching encryption key separately and review recovered configuration before selecting it for a running service.


## Account and team upgrade

Every account can inspect its identity and change its own password at `/account`.
The change requires the current password and an unused authenticator code when
a factor is enrolled. It signs out every device and invalidates outstanding
password links, while preserving the account role, team memberships and factor.
Failed attempts are rate limited and audited without recording supplied credentials.

Migrations 0012 to 0014 introduce session security versions, team membership and
nullable team ownership on operational records. Existing work remains personal to
its recorded creator; no team assignment is guessed. Legacy conflicting links are
preserved and recorded as `legacy_scope_conflict` audit entries, but cannot be used
to create new cross-scope work. Orphan alerts without an established owner are
administrator-only. See [scoped work](api/SCOPED_WORK_API.md) and
[teams](api/TEAMS_API.md) for permissions and request fields.

Back up the database and retain the matching encryption key before applying the
normal migration procedure to an operator installation. No operator database was
migrated during this work. The app can upgrade a still-valid old refresh cookie,
while access tokens lacking the new family/version claims are rejected. Removed
or deactivated accounts and revoked sessions must sign in again.

Do not treat an Alembic downgrade as a complete security rollback: older code has
no manager role or team privacy boundary. Restoring a verified pre-upgrade backup
into a new destination is the recovery path, with a deliberate review of any work
created since that backup. Ordinary team members cannot write archived teams;
administrators retain explicit manual oversight. Automation stops for archived
teams even when its owner is an administrator.
