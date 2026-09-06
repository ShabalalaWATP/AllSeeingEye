# Administrator AI connections

Requested 6 September 2026. This extends the automated research plan with
administrator-controlled provider, model, reasoning and credential selection.
The user explicitly selected OpenAI GPT-5.6 Luna at Max reasoning, superseding
the earlier free-only model-provider constraint for this connection.

## Required behaviour

- [x] Administrator-only encrypted credential input, provider presets and a model
  picker populated from the configured account's advertised models.
- [x] Exact OpenAI base `https://api.openai.com/v1`, model `gpt-5.6-luna` and
  `max` reasoning supported throughout text generation, including challenge,
  direction, translation and connection tests.
- [x] Configure a replacement, test its saved configuration, then explicitly
  apply it. Failed or stale tests cannot activate a connection.
- [x] Global connection applies to personal work and teams without an override,
  including administrator-created work. Team overrides follow the work's scope.
- [x] Team inheritance is explicit. A broken override fails closed rather than
  sending that team's material to another provider without agreement.
- [x] In-flight work uses one captured configuration; switches affect new work.
  Existing report evidence and results are unchanged.
- [x] Bound profiles cannot be edited or deleted underneath an active connection.
  A replacement is tested and applied separately. API keys never return to the
  browser or appear in diagnostic response bodies or audit records.
- [x] Discovery and tests use bounded requests without redirects; fresh authority
  is checked after outbound work and before storing a test result or activation.
- [x] UI exposes loading, failure, empty catalogue, manual model entry, test
  result, affected scope and successful activation without technical clutter.
- [x] SQLite/PostgreSQL migration and routing regressions, gateway request tests,
  frontend tests, browser review, static checks and security review completed.
- [ ] Actual account connection tested after the administrator supplies the key
  through the app. Do not substitute scripted tests for account access evidence.

## Interface direction

Use the existing restrained dark application surfaces and one action accent.
Lead with the current global connection, followed by a divided team override
list. A replacement editor has three clear steps: configure, test and apply.
Keep advanced token and role settings collapsed. A confirmation names the
destination scope and explains that explicit team overrides remain in place.

The API key field is a password input. An existing key is represented only by
its stored hint; blank means preserve the existing key where the endpoint is
unchanged. Never reuse a saved key automatically at a changed endpoint origin.

The model catalogue advertises account-visible IDs, not proof that each model
supports report generation. The connection test checks the selected text model
and structured-output contract. Embeddings remain a separate model role because
Luna is a text-generation model, not an embedding endpoint.

## Verified provider contract

OpenAI documents `gpt-5.6-luna` with reasoning efforts none, low, medium, high,
xhigh and max, and support for Chat Completions and structured outputs.
[Luna model](https://developers.openai.com/api/docs/models/gpt-5.6-luna).
Retain the existing Chat Completions adapter; use the supported modern reasoning
parameters and keep compatibility with existing local endpoints.

Account model discovery uses `GET https://api.openai.com/v1/models`.
[List models](https://developers.openai.com/api/reference/resources/models/methods/list).
Reasoning and visible output share the completion token budget. The new OpenAI
preset uses a bounded 16,000-token budget; Max may take longer and consume more
tokens. Account-specific access and actual quality still require a real test.

## Verification evidence

The connection-specific backend selection passed 40 tests with 97.24%
branch-inclusive scoped coverage. Separate routing checks passed 40 tests with
100% scoped coverage; these focused counts overlap the wider suite and must not
be added together. Forty-two connection/lifecycle/routing integration tests also
passed against a disposable PostgreSQL 17 database. Six migration checks passed
across SQLite and PostgreSQL, including retained legacy encrypted configuration,
ordered probe defaults, assignment counters and safe downgrade refusal.

Browser checks exercised configure, discover, test, keyboard confirmation and
global/team activation at 1440, 390 and 320 pixels with synthetic API responses,
no horizontal overflow and no page errors. The focused
[security review](security/AI_CONNECTIONS_REVIEW.md) records two reproduced and
fixed findings. No live API account test, operator migration, deployment or remote
CI run is included in this evidence.

The broad backend run completed with 1,533 passed, one failed and five skipped,
measuring 96.54% branch-inclusive application coverage (90% gate met). The failure
used an old legacy-profile cleanup fixture imported before its correction: the
new API correctly refused deletion, leaving a duplicate profile name in the
test. Cleanup now uses the explicit migrated-state repository fixture. The entire
four-test direction/advocacy file passed on a fresh rerun. No production gate was
relaxed and no application failure remained identified. All five PostgreSQL-only
skips passed in separate disposable PostgreSQL runs, including the existing
refresh-race and scope-migration tests. The broad run itself is not recorded as
an entirely green invocation.

Ruff, formatting, strict mypy across 383 application/evaluation source files,
architecture import contracts, Bandit and file-length checks passed. No dependency
was added. The final frontend run passed 472 tests across 92 files, with 98.41%
line coverage and 91.62% branch coverage. Lint, both TypeScript configurations,
formatting and production build passed; the existing map/deck chunk-size warning
remains. Browser checks also reused one saved connection for another team without
another save, key entry or hidden edit/delete controls. There were no page errors
or horizontal overflow at 1440, 390 and 320 pixels.
