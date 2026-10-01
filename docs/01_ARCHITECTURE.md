# Architecture

[Documentation](README.md) · [Setup](SETUP.md) · [Sources](02_DATA_SOURCES.md) · [AI](AI.md)

The All Seeing Eye is a modular monolith: one Python application owns collection,
research and saved work, and a React client provides the interface. External feeds
and model providers sit behind adapters. A relational database stores durable
records; a bounded in-memory store holds the live public event stream.

This keeps a self-hosted installation manageable while giving individual parts
of the code clear responsibilities.

## The stack

| Area | Technology | Role |
| --- | --- | --- |
| Browser | React 19, TypeScript, Vite, Tailwind CSS | Workspaces, forms and report readers |
| Maps | MapLibre GL, deck.gl | Globe, flat map, observations and overlays |
| Specialised graphics | Three.js; OGL | Selected 3D views; animated Eye branding |
| Client state and validation | Zustand, Zod | Shared session/live state and validated API responses |
| API | Python 3.13+, FastAPI, Pydantic | Typed HTTP endpoints and server-sent events |
| Persistence | SQLAlchemy, Alembic | Database access and schema migrations |
| Databases | SQLite for native development; PostgreSQL for Compose | Accounts, research, reports and configuration |
| Model access | OpenAI-compatible HTTP APIs; AWS Bedrock Converse | Configurable AI connections behind gateway ports |
| Serving | Caddy, Docker Compose | HTTPS, static files and API proxying |
| Tooling | uv, pnpm, pytest, Vitest, Ruff, mypy, ESLint | Locked dependencies, tests and static checks |

Exact versions are recorded in [backend dependencies](../backend/pyproject.toml),
[frontend dependencies](../frontend/package.json), their lockfiles and
[Compose](../docker-compose.yml). The Compose database uses a PostGIS image;
the application does not require a separate vector database.

### Download budgets

`pnpm check:bundle` runs after every build in CI and prints two gzip totals:

- Initial JavaScript, which every visitor downloads before the first page,
  including sign-in: budget 240 KiB (measured 196 KiB on 1 October 2026).
- The globe route, the default landing page: the static closure of the
  `GlobePage` chunk and the MapLibre worker, less what the initial load already
  fetched. Budget 850 KiB (measured 772 KiB on 1 October 2026), mostly
  MapLibre, deck.gl and the page itself.

The check also fails when a lazy-only library loads on first paint, when the
measurement or area research panels return to the globe's static closure (they
load when their tool opens), or when a fixed-name MapLibre worker or shared
module ships. MapLibre's worker is built as an extra entry of the same graph, so
the main thread and the worker import one content-hashed shared chunk: a cold
load downloads it once, Caddy serves it immutable, and a deploy cannot pair old
main-thread code with a new worker.

## System context

![C4 system context: researchers use the app, which reads public sources and can call configured AI and email services](diagrams/system-context.svg)

## Application containers

![C4 container diagram: browser, web server, API, database and isolated parser with external service boundaries](diagrams/containers.svg)

These are logical C4 views, not a map of a particular server. Their source is
the [Structurizr workspace](diagrams/workspace.dsl); see
[diagram maintenance](diagrams/README.md) to validate or regenerate them.

The Compose stack separates the web server, API, database and file parser. The
parser has no network access and receives bounded extraction requests over a
local socket. Native development uses an isolated subprocess instead.

**Run one API process.** Live events, rate limits, model admission and parts of
background coordination are process-local. Adding HTTP workers requires a
shared-state design, not just a higher worker count. The parser is a separate
worker for untrusted files, not another API instance.

## From a feed to the map

```mermaid
flowchart LR
    A[Feed or API] --> B[Fetch within source limits]
    B --> C[Normalise and attach provenance]
    C --> D[Resolve location and grade]
    D --> E[(Bounded live event store)]
    E --> F[HTTP snapshot]
    E --> G[Server-sent updates]
    F --> H[Globe, map and trackers]
    G --> H
    E --> I[Warning rules and selected research evidence]
```

Collectors preserve source identity, dates, location precision and grading
rationale. The browser loads a snapshot and then receives updates and expiries
through an authenticated stream. A stream gap triggers a new snapshot.

An empty map can mean no matching retained observations, a disabled layer or an
unavailable source. It does not prove that nothing happened in an area.

## From a question to a saved report

```mermaid
flowchart TD
    Q[Question or saved Research Brief] --> S[Resolve scope and current access]
    S --> C[Bounded collection from supported sources]
    C --> E[Select and grade evidence]
    E --> F[Freeze evidence and collection receipts]
    F --> M[Configured model drafts structured findings]
    M --> V[Validate citations, structure and assessment rules]
    V --> R[Save report version and evidence]
    R --> U[Review, export or follow up]
```

On-demand collection is private to the research operation. Selected evidence and
receipts are saved with the report; unselected results do not become a growing
shared archive. The report job records progress separately from a browser tab.
Retries reuse admitted work when the request identity is unchanged. A regenerated
report is a new version, with its requirements and brief provenance retained.

Subscriptions add scheduling, durable editions, retry controls and optional
comparison with the previous successful report. Pausing stops future admission;
it is not a promise to undo an external model call already made.

Research tiers count admitted runs through a shared application service. Durable
jobs and subscriptions commit admission and usage together; synchronous report
generation reserves its run before model work. Separate daily and weekly counters
preserve usage across tier changes and deletion. Provider-call and token accounting
remain separate. See [the research tier decision](adr/0020-per-user-research-tiers.md).

The [AI guide](AI.md) explains provider routing and which checks are deterministic.

## Code boundaries and SOLID

```text
backend/src/ase/
  domain/          Entities, values, assessment rules and pure calculations
  application/     Use cases and protocol ports
  adapters/        Persistence, feeds, AI, exports and other external systems
  api/             HTTP routes, transport schemas and request dependencies
  infrastructure/  Settings, logging and process services
  container/       Construction and wiring of concrete dependencies

frontend/src/
  app/             Routes, session boundaries and application shells
  features/        Individual workspaces and their interactions
  components/      Shared interface components
  lib/             API clients, schemas, shared policy and hooks
  stores/          Shared browser state
```

The project applies **SOLID principles pragmatically**. The goal is to make
behaviour easier to change and test without spreading one change across the app.

| Principle | How it is applied |
| --- | --- |
| Single responsibility | Routes handle HTTP, use cases own policy, adapters perform external work. UI hooks own asynchronous state while components render and handle interaction. |
| Open/closed | Source and model implementations plug into shared contracts. Adding a provider should not require rewriting report policy. Registration and configuration remain explicit. |
| Liskov substitution | Adapters must preserve the same result, failure and cancellation semantics. Contract and regression tests check behaviours such as model output exhaustion. |
| Interface segregation | Focused protocol ports and component inputs expose what a consumer needs. Capability metadata makes optional provider behaviour explicit. |
| Dependency inversion | Domain and application logic depend on inward-facing types and ports. The composition root supplies concrete persistence, network and model implementations. |

Import-linter enforces backend dependency rules. ESLint prevents frontend
features from importing one another directly; shared behaviour belongs in shared
modules. Strict typing and behaviour tests support these boundaries.

This is a design practice, not a certification of perfect separation. A small
explicit exception list remains for subscription read projections, and some
subscription coordination lives in the composition package. The enforced
contracts are the source of truth, rather than file size or a SOLID score.

### Accessibility checks in the frontend tests

- **axe-core** runs on representative pages through the real route table and on the
  shared primitives (`frontend/src/test/a11y/`, `components/ui/primitives.a11y.test.tsx`).
  Any violation fails CI with the rule, the element and a link to the fix. The helper,
  `src/test/axe.ts`, also fails when an axe check throws, so a rule cannot be skipped silently.
- **jsdom limits.** jsdom has no layout or paint, so `color-contrast`, `link-in-text-block`
  and `target-size` are off there. Contrast is measured from the theme tokens instead
  (`styles/paletteClasses.test.ts`, `styles/readability.test.ts`) for every palette.
  Text tokens must reach 4.5:1. The focus ring, accent borders, control borders and
  chart marks must reach 3:1.
- A browser pass is still needed for contrast over imagery, zoom, reflow and screen reader
  behaviour. Passing these tests is not a WCAG conformance claim.

### Shared interface primitives and design tokens

- **Primitives** live in `frontend/src/components/ui`. Every route page names itself
  through `PageHeader`, which has one heading size per page type: workspace and sign-in
  pages, records and tools, and status pages. `Tabs` is the one tab strip. Route tabs are a
  labelled navigation of links; panel tabs are WAI-ARIA tabs. `Skeleton` draws
  placeholders beside a status message. Confirmations use `ConfirmButton` and
  `ConfirmDialog`; empty lists use `EmptyState`.
- **One type scale.** `styles/theme.css` resets Tailwind's font sizes and declares the
  scale (`text-2xs` to `text-4xl`, plus a display `text-6xl`) in rem, so text follows the
  reader's font size. `styles/typeScale.test.ts` rejects arbitrary sizes such as
  `text-[11px]`, undeclared steps and any `h1` outside `PageHeader`. The listed exceptions
  are the paper report reader, the globe's visually hidden heading and, until its pending
  rewrite lands, the alerts page.
- **Colours come from tokens.** Theme-dependent colours use the `--color-*` tokens. Fixed
  palettes are named once at the top of their stylesheet: the paper report, the sign-in
  screen and the radio planner instrument. `styles/featureColours.test.ts` rejects a hex
  colour outside a custom property declaration and any hex colour in a component class.
- Some globe stylesheets and panels are temporarily exempt from the type-scale and
  colour checks while the globe is being refactored. Each exemption fails its own test once
  it is no longer needed.

## What is stored

| Data | Lifetime and location |
| --- | --- |
| Live public observations | Bounded in-memory retention; one disposable, size-capped snapshot file is reloaded through the same retention after a restart ([ADR 0022](adr/0022-live-store-snapshot.md)) |
| Reports and selected evidence | Durable report versions with frozen provenance and assessments |
| Research Briefs, subscriptions, jobs and team work | Durable records with current access checks |
| Accounts, sessions, source and AI configuration | Database; sensitive connection values are encrypted |
| Supplied research files | Bounded, expiring private inputs; original-file retention requires the relevant explicit workflow |
| Satellite orbital inputs | Bounded replacement cache and request cooldowns; propagated positions are recomputed |
| Report search embeddings | Bounded index of selected saved reports, separate from raw live events |

Reference catalogues and small operational aggregates have their own bounded
storage. A saved excerpt or source URL is not proof of authenticity, and does not
imply that a complete original website was archived.

## Access and external work

Personal and team records have object-level access checks. Background work checks
the current owner, membership and team state too. Sensitive mutations serialise
authority checks with relevant account/team changes; long network and model
calls run outside those locks, followed by a fresh access check before release.

Feed URLs, document input and model output are untrusted. Outbound requests,
parsing and rendering use separate bounded adapters. See
[security and privacy](07_SECURITY_BY_DESIGN.md) for the relevant controls and
[self-hosting](DEPLOYMENT.md) for deployment requirements.
