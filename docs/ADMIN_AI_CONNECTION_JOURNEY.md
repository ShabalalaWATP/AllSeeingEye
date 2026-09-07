# Administrator AI connection setup

Implementation and acceptance record, 7 September 2026. Administrators manage connections in
the dedicated administration area. Ordinary accounts cannot discover saved keys,
change connections or assign model providers.

## Setup journey

1. Choose OpenAI, Amazon Bedrock or a custom OpenAI-compatible endpoint and enter
   its credential. OpenAI supplies `https://api.openai.com/v1` automatically.
2. Load the account catalogue during setup, search/select a model and choose
   reasoning effort. A catalogue entry is not proof of text/structured-output
   compatibility. Bedrock currently requires a model or inference-profile ID.
3. Test the selected saved draft. This makes a synthetic provider request and can
   consume provider tokens. Changing its settings requires a fresh successful test.
4. Review the audience and confirm the switch. Saving, discovering and testing
   alone do not switch the application's text provider.

Discovery of unsaved settings does not store a placeholder profile or credential.
A saved credential may only be reused for the same provider and endpoint. API
errors never return provider response bodies or credentials. Saved keys remain
server-encrypted; active connections are replaced through separately tested drafts.

## Audience rules

| Destination | Selected connection |
| --- | --- |
| Personal research | Destination owner's personal override, otherwise app default |
| Team research | Team override, otherwise app default |
| Shared feed translation | App default |
| Shared semantic indexing | Separate embeddings configuration |

Personal overrides never redirect team research. An administrator regenerating
another person's report uses that report owner's personal routing. Each run
freezes the selected settings for its text roles, preserving provenance. Existing
runs and historical reports retain their recorded settings. An invalid assigned
configuration fails closed rather than selecting an unrelated provider.

The final confirmation must distinguish an app-default change from an override.
An app-default change affects users and teams inheriting that default; explicit
team and personal overrides remain. Personal changes affect that person's
personal workspace only. Resetting an override restores inherited routing.

## Reference and acceptance

The official [OpenAI model-list reference](https://developers.openai.com/api/reference/resources/models/methods/list)
confirms `GET https://api.openai.com/v1/models` and bearer authentication. The
[Luna model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
records `gpt-5.6-luna` and reasoning levels none, low, medium, high, xhigh and max.
These references were checked on 7 September 2026. Available model identifiers
come from the configured account rather than a hard-coded exhaustive catalogue.

Backend acceptance passed 87 cases in the initial affected regression group.
Two fixture failures were repaired and verified: 10 migration/routing cases and
the saved-discovery regression passed. Five personal API/integration cases also
passed on a disposable PostgreSQL database. Migration 0028 passed SQLite and
PostgreSQL schema parity, preservation, downgrade refusal with personal overrides
and clean downgrade/re-upgrade. The disposable container was removed.

Unsaved discovery passed 14 API cases; 33 existing adapter/lifecycle cases passed.
Mypy (568 source files), Ruff, two architecture contracts and configured Bandit
passed. Focused review found and repaired an account-switch retry race in the
administrator's apply/reset calls. These requests now carry authority-bound abort
signals. No unresolved blocking review finding remains.

Logs: `data/personal-routing-tests.log`, `data/personal-routing-postgres-runtime.log`,
`data/llm-draft-discovery-tests.log`, `data/llm-discovery-regression.log`,
`data/llm-saved-discovery-final.log` and `data/admin-journey-*`.
Final frontend integration passed all 222 tests in 35 files, including admin
journeys, authority changes, Bedrock compatibility, map export and API retries.
OpenAPI/types were regenerated and the production build passed. Scoped ESLint,
TypeScript, UTF-8/LF, file-length and whitespace checks passed. The existing large
map-vendor chunk advisory remains. These checks do not replace live provider or
browser/GPU acceptance. Full-suite coverage was not remeasured.
Logs: `data/admin-map-integration-final.log`, `data/admin-map-build-final.log` and
`data/admin-map-eslint-final.log`.

Migration 0028 is ready but has not been applied to operator data. Back up the
operator database and apply the application's normal migration procedure before
running this version against an existing installation. Live provider acceptance
remains separate: these tests use synthetic credentials and fake model gateways.
No live API key or default model assignment has been changed.

Subsequent full frontend acceptance passed 946 tests with 90.18% branch coverage
(see `AUTOMATIC_RESEARCH_PLANNING.md`). Additional failure/proof/cancellation
tests found a safe connection-test reason being replaced by generic error copy.
The journey now preserves that public reason while retaining all successful-test
and scope-confirmation safeguards. Full lint, types and the production build
passed again. This does not establish a live provider connection.
