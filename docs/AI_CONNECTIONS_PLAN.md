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

## Native Bedrock extension

Requested 6 September 2026. Administrators can now select **Amazon Bedrock**,
choose an AWS region and enter a Bedrock API key plus a model or inference-profile
ID. This uses native Converse structured outputs through an explicit provider
adapter. OpenAI and custom compatible profiles retain their existing protocol.
See [ADR 0013](adr/0013-native-bedrock.md) and the
[operator flow](AI_CONNECTIONS_OPERATIONS.md#amazon-bedrock).

- [x] Native text provider, encrypted keys, canonical regional destination and
  manual model selection, with provider-specific inference validation.
- [x] Existing saved-configuration test, explicit global/team assignment and
  captured in-flight provider routing retained across every text stage.
- [x] Migration `0018` preserves legacy tested hashes and assignments, expands
  credential/model storage, and refuses downgrades that would damage compatibility.
- [x] Frozen reports record provider; old records remain readable without rewriting.
- [x] Scripted HTTP production covers direction, invalid report repair, challenge,
  redraft and review through the actual native adapter.
- [x] Eighteen migration cases pass across disposable SQLite and PostgreSQL 17,
  plus two pagination checks. These preserve legacy tested assignments and prove
  refusal before DDL for incompatible credentials, identifiers and frozen history.
- [x] Forty-two native adapter/schema/production tests pass. The nearest 68
  profile/key/administration tests pass with 97.22% focused branch-inclusive
  coverage; the final raw-provider-type regression also passes separately.
- [x] Final review repaired a native completion-budget mismatch. All Bedrock text
  stages now honour the configured budget rather than silently applying legacy
  stage caps. Forty-nine adapter, production, propagation and budget checks pass
  after this change; the ordinary OpenAI-compatible stage caps remain unchanged.
- [x] Frontend validation: 504 tests pass, 98.46% line coverage and 91.86% branch
  coverage. Lint, types and build pass. Browser checks at 1440, 390 and 320 pixels
  complete native save/test/apply with no discovery request, overflow or page error.
- [x] Independent [security review](security/BEDROCK_REVIEW.md) closed the historical
  routing downgrade issue. Its synthetic selection passed 105 tests, with nine
  PostgreSQL variants verified separately by the migration worker. No other
  concrete security vulnerability remained in the reviewed change.
- [ ] Actual AWS account access and representative research-quality evaluation.

This slice does not add IAM role authentication, automatic key renewal, AWS
catalogue discovery, embeddings or model-specific reasoning controls. The standalone
evaluation CLI remains OpenAI-compatible. No live AWS call or operator migration
is included in development evidence.

The broader backend snapshot passed **1,624 tests with 10 skipped** in 699.18
seconds, meeting the 90% gate with **96.47% branch-inclusive coverage**. That run
started before the final token-budget correction and late migration-history tests;
the final 49-test native/production selection and separate migration/pagination
runs above cover those changes. Counts overlap and are not additive. Ruff,
formatting, strict mypy across 380 source files, Bandit, architecture import
contracts and file-length checks passed. No dependency was added.

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
At the official OpenAI base URL, explicit Max requests use the native Responses
route. Other reasoning settings and compatible endpoints retain Chat Completions.

Account model discovery uses `GET https://api.openai.com/v1/models`.
[List models](https://developers.openai.com/api/reference/resources/models/methods/list).
Reasoning and visible output share the completion token budget. The new OpenAI
preset uses a bounded 32,000-token budget. Two observed 16,000-token photo report
drafts exhausted their full budgets on reasoning without producing an answer.
The larger preset is headroom, not a completion guarantee. It applies to new Luna
connections; saved and manually entered budgets remain unchanged. Other provider
defaults and independent source/web limits remain unchanged. Max can take longer
and consume more tokens. Account-specific access and actual quality still require
a real test.

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
