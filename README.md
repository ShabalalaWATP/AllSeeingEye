# The All Seeing Eye

The All Seeing Eye is a self-hosted workspace for open-source intelligence
(OSINT). It brings public observations onto a globe and map, lets you research a
question, and saves the resulting assessment with the evidence used to produce it.

The main workflow is simple: **observe, ask, collect, assess, review**. AI helps
with planning and writing. Source records, grades, collection gaps and citations
remain available so you can check the result.

![The All Seeing Eye globe with navigation and map controls](docs/images/globe.png)

*The current app interface, captured locally with an illustrative account and
sample observations. Screenshots are not a statement of live source coverage.*

[Set up the app](docs/SETUP.md) · [Using the app](docs/04_FEATURES_AND_VIEWS.md) ·
[Documentation](docs/README.md)

## What you can do

- **Explore the live picture.** Switch between globe and map, filter observations,
  inspect source details, measure areas and distances, and save map views.
- **Work with map tools.** Save editable drawing collections, research the same
  boundary, compare radio studies and inspect terrain. The [map workspace guide](docs/MAP_WORKSPACE.md)
  explains the tools and their limits.
- **Research a question.** Choose countries, regions, dates and research depth.
  Add supported private inputs or start from a selected map area. Save reusable
  Research Briefs with your requirements.
- **Read the evidence behind an answer.** Reports retain selected evidence,
  collection receipts, source grades, uncertainty and model details. Review saved
  versions, follow up on a question, or export a report.
- **Keep a subject under review.** Subscriptions run research on a schedule and
  retain editions, progress and retry controls.
- **Use specialist workspaces.** Live monitoring, Ukraine, cyber intelligence,
  economy and photo geolocation provide focused ways to explore their subject.
- **Share work with a team.** Personal and team scopes control access to saved
  work. Administrators manage accounts, sources, model connections and usage.

![Research workspace with an example question and scope controls](docs/images/research.png)

*Research begins with a question and an explicit scope. This example uses local
sample data and does not submit a model request.*

## Where the information comes from

The app combines public feeds and APIs, on-demand research connectors and
packaged reference data. Examples include USGS, NASA, NOAA, public news and
humanitarian publishers, aviation and maritime data, CelesTrak orbital inputs,
cyber advisories and economic series.

These sources have different coverage, update intervals, licences and access
requirements. Some need credentials or an approved account. A catalogue entry
is not a promise that its provider is available or that every item has a precise
location. The source screens show the installation's actual state.

See [sources and coverage](docs/02_DATA_SOURCES.md) for the source families,
optional connections and how to interpret their status.

## How AI is used

An administrator chooses and tests the model connection. The app supports
OpenAI-compatible endpoints and native Amazon Bedrock; features such as vision,
embeddings and fresh web search depend on the selected provider and model.
There is no bundled model that must be used.

AI can plan collection, draft reports, challenge an assessment, translate text
and suggest photo-location leads. Application code handles access, collection
limits, source grading and structured validation. A source grade, model answer
or passing validator does not establish that a claim is true.

Browsing the map does not require an AI account. Cloud AI calls send the relevant
context to the configured provider and can incur charges. See [AI in the app](docs/AI.md)
for routing, privacy, capabilities and usage controls.

## Architecture and engineering

The application uses a Python/FastAPI backend and a React/TypeScript frontend.
MapLibre GL and deck.gl render the map and globe. SQLite supports native
development; Docker Compose runs PostgreSQL, an isolated file parser, the API
and Caddy. Live observations stay in a bounded memory store. Saved research,
selected evidence, accounts and configuration are durable.

The code follows **SOLID principles** through focused use cases, narrow protocol
interfaces, replaceable adapters and explicit dependency injection. Routes and UI
components delegate policy and asynchronous work to dedicated modules. Backend
import contracts, frontend feature boundaries, strict typing and regression tests
help enforce that design. This is a practical standard, not a claim of perfect
separation.

Read the [architecture guide](docs/01_ARCHITECTURE.md) for the stack, Structurizr
C4 diagrams, data flows and concrete SOLID examples.

## Run it on your machine

Choose one of the two routes in the [setup guide](docs/SETUP.md):

| Route | What you need | What it runs |
| --- | --- | --- |
| Native development | Git, uv, Python 3.12+, Node 22.12+ and the pinned pnpm version | API, SQLite and Vite |
| Docker Compose | Git and Docker with Compose | Packaged app, PostgreSQL and isolated parser |

The guide covers **Windows 11, macOS and Linux**, including Apple Silicon
container requirements, configuration, the first administrator, MFA and local
certificates. AI and keyed sources are optional additions after sign-in.

For a hosted installation, use [self-hosting guidance](docs/DEPLOYMENT.md).
Reader-facing documentation describes the deployment contract without publishing
an individual server's addresses, login details or recovery paths.

## Limits to understand

Public sources are incomplete and sometimes delayed, blocked or unavailable.
Country-level locations are not exact event coordinates; calculated satellite
positions are not direct observations. Similar reports may share an original
source and should not be counted as independent confirmation.

Saved evidence supports traceability, not automatic authentication. Check the
original sources, dates, assumptions and contrary evidence before relying on a
report. Photo geolocation produces candidates to investigate. Provider compatibility
tests and software tests do not measure research accuracy.

## Contributing and checks

Start with [architecture](docs/01_ARCHITECTURE.md) and the repository conventions
in [CLAUDE.md](CLAUDE.md). Use the committed lockfiles. Run backend checks from
`backend`:

```text
uv run ruff check src tests
uv run ruff format --check src tests alembic
uv run mypy src
uv run lint-imports
uv run pytest
```

Run frontend checks from `frontend`:

```text
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

CI also runs PostgreSQL tests, coverage gates, dependency and security checks,
and container builds. Keep new behaviour covered by meaningful tests and keep
source, AI and setup documentation aligned with the code.
