# Sources and connections

Implemented 13 September 2026. Open **Settings**, then **Sources and connections**
(`/sources`). The page is available to every signed-in user and answers two
questions the old catalogue could not: which registered sources are actually
collecting on this server, and which API keys or local requirements are missing.

## What the page shows

| Section | Content |
| --- | --- |
| Connection totals | Five tiles: collecting, needs attention, key or setup missing, on demand, switched off. Selecting a tile filters the catalogue. |
| Needs attention | Sources that cannot collect: a required credential is absent, a local runtime or snapshot is missing, or the source is failing after repeated errors. Each row names the server setting that unlocks it. |
| Platform connections | Services that are not sources: the AI assessment model for the viewer's personal workspace, credential encryption, Ordnance Survey maps, email delivery, Washington highway cameras, the alert webhook, Wayback archiving, conflict screening, local OCR and video tools and the optional PDF runtime. |
| Source catalogue | Every scheduled feed and on-demand research capability with a connection badge, delivery health, the requirement note, coverage, language, access and the editorial rating. A new Connection filter joins topic, country, language, collection and access. |

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
| `disabled_by_environment` | Excluded by `ASE_FEEDS_DISABLED`. |

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

## Limits

- The FIRMS credential origin is read per request; other requirements reflect
  process settings and need an API restart to change.
- `key_unverified` relies on delivery health; a wrong key shows as `degraded` or
  `failing` after the first attempts, not immediately.
- Research capabilities cannot be health-checked without a query, so they stay
  `on_demand` even when a provider is unreachable at that moment.
- Platform connection checks are configuration facts, not live probes. The AI
  model entry resolves the viewer's personal routing; team routing is shown in the
  research workspaces themselves.
