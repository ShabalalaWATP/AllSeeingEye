# Sources and connections

Implemented 13 September 2026. Open **Settings**, then **Sources and connections**
(`/sources`). The page is available to every signed-in user and answers two
questions the old catalogue could not: which registered sources are actually
collecting on this server, and which API keys or local requirements are missing.

## What the page shows

| Section | Content |
| --- | --- |
| Catalogue summary | Totals by state (live or available, on demand, needs key or setup, blocked upstream, retrying or failing, off by operator choice) and by family (scheduled feeds, on-demand research, camera indexes, map layers and services, Ukraine tracker datasets, reference datasets). Selecting a tile filters the catalogue. |
| Needs attention | Actionable items only: an upstream that refuses this server or account (with its fixed reason), a feed paused by the circuit breaker, or a required key or setup step with the setting that unlocks it. Optional settings, on-demand tools, operator switches and short retries are not listed. |
| Platform connections | Services that are not sources: the AI assessment model for the viewer's personal workspace, credential encryption, Ordnance Survey maps, email delivery, the alert webhook, live feed collection, Wayback archiving, conflict screening, local OCR and video tools and the optional PDF runtime. Toggles report the effective state, including defaults, so archiving and feed collection show as on outside tests without an explicit setting. |
| Source catalogue | Every scheduled feed and research capability grouped by topic, then camera providers, map layers, Ukraine datasets and reference datasets grouped by family. Filters: family, connection, topic, country, language and access. Topic, country and language apply to feeds and research only. |

Updated 15 September 2026: the page now also lists data the app uses outside the feed
scheduler and research registry. An in-process count on that date gave 305 feeds and
research capabilities plus 122 assets: 98 camera providers, 13 map layers and services,
8 Ukraine tracker datasets and 3 reference datasets. Sanctions designation snapshots and
AidData stay in the research family, where they were already listed.

## Connection states

| State | Meaning |
| --- | --- |
| `connected` | Scheduled feed, last collection succeeded. |
| `idle` | Scheduled feed registered, no collection attempted yet. |
| `key_unverified` | A credential is configured but no collection has succeeded yet. |
| `degraded` | Recent attempts failed; the scheduler is retrying with backoff. |
| `failing` | The circuit breaker paused the feed after repeated failures; an administrator resets it under Admin, Sources. |
| `key_missing` | A required API key or credential pair is not configured, so the connector is not built. |
| `not_configured` | A non-key requirement is absent: a local snapshot, catalogue, runtime or acknowledgement. |
| `on_demand` | A research capability queried only when a run selects it. Optional keys keep this state. |
| `disabled_by_admin` | Switched off through source controls. |
| `disabled_by_environment` | Off by operator choice: excluded by `ASE_FEEDS_DISABLED`, live feed collection switched off (`ASE_FEEDS_ENABLED=false`, the test default), an optional toggle left off, or a Ukraine frontline provider whose terms are not recorded. |
| `blocked_upstream` | The publisher refuses this client, registration or account tier. The reason is fixed server text from `FeedBlocked`, shown to every signed-in user: CISA and ACSC advisory refusals, a ReliefWeb appname that is not pre-approved (HTTP 403), and an ACLED account without API access (HTTP 403 on data reads; Research, Partner or Enterprise tiers are needed). |
| `available` | A packaged snapshot or curated catalogue is present and served without an upstream request. |

A missing requirement outranks every other reason, so an operator sees the
setting to add first. Optional requirements (the UCDP token, the OpenAlex key, the
alert webhook, archiving, screening, the PDF runtime) never mark a source as
missing; they are labelled optional.

## How the inventory is built

`ase.application.source_inventory.SourceInventory` merges three lists: live
connectors from the scheduler, on-demand research specifications, and the keyed
connectors that the registry only constructs once their credential exists
(AISStream, BarentsWatch AIS, ACLED and the ReliefWeb API). Without this third
list the catalogue silently omitted unconfigured keyed feeds. Requirements are
computed in the composition root (`ase.container.source_inventory`) from settings
and, for NASA FIRMS, from the encrypted administrator credential store; only a
boolean and an origin (`environment`, `database`, `none`, `unknown`) leave the
server. Health comes from the shared registry with error text removed, because
error messages can embed operator URLs.

The APIs are `GET /api/sources` (each item now carries `connection`) and
`GET /api/sources/connections`. Both are authenticated, marked `private,
no-store`, and never include URLs, credential values or error text. Setting
names are documented in `.env.example` and are not secrets; ordinary users can
see whether a key is present so they understand why a layer or research
capability is empty, but only the operator can change it.

Data assets come from `ase.container.source_assets`. Camera providers are read from the
camera service's registered sources and cached status only (`snapshot`, no refresh), and
classified by adapter class as official index, curated catalogue or third-party directory.
Map layers and datasets use the same cached loaders as the map, Ukraine and reference
endpoints, so attribution, licence text and snapshot dates come from the resource files.
Browser-direct base maps and request-time services (terrain, place search, routing) name
their public provider without contacting it. Nothing new is persisted.

Upstream refusals use `FeedBlocked`, a `FeedDeferred` subclass. The scheduler records its
message as `blocked_reason` in health; any later success, failure, throttle or reset clears
it. Other deferral text, such as cache cooldowns, is never exposed because it can embed
operator URLs.

## Limits

- The FIRMS credential origin is read per request; other requirements reflect
  process settings and need an API restart to change.
- `key_unverified` relies on delivery health; a wrong key shows as `degraded` or
  `failing` after the first attempts, not immediately. ReliefWeb and ACLED refusals show
  as `blocked_upstream` after the first refused poll. A manually supplied ACLED access
  token uses the shared client, which hides status codes, so only the refresh-token path
  reports the entitlement reason.
- Camera providers that have not been opened on the map show as on demand; their state
  reflects the last cached refresh in this process, not a live probe.
- Research capabilities cannot be health-checked without a query, so they stay
  `on_demand` even when a provider is unreachable at that moment.
- Platform connection checks are configuration facts, not live probes. The AI
  model entry resolves the viewer's personal routing; team routing is shown in the
  research workspaces themselves.
