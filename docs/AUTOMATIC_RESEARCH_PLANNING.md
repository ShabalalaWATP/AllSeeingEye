# Automatic candidate and challenge planning

Implementation and acceptance record, 7 September 2026. This advances E3 of the full research
expansion plan. Semantic quality and live-model acceptance remain independent
gates, not consequences of passing schema tests.

## Production behaviour

One bounded planning call supplements public-source research before collection.
It uses the run's frozen direction-role connection, including the destination
owner's personal override or the team's routing. It receives the question,
original terms, supplied identifiers, declared scope and concrete selected-source
capabilities. Source evidence is not yet available at this stage.

The model can propose candidate hypotheses and challenge/disambiguation searches.
It cannot select arbitrary URLs, invent registry identifiers, change the time
window, country, languages, subject, area or source selection, replace operator
entries, execute code or increase collection limits. Proposed identifiers must
be anchored in the actual question, explicit operator terms, supplied subject or
operator hypotheses/tasks. Terms inferred by the earlier direction model cannot
ground a new identifier. Hypotheses remain unverified interpretations,
not matches, ownership relationships or evidence.

Validate the complete response and each proposed task against the current source
inventory. Only explicitly supported term-search adapters may execute generated
term searches. Subject-only registry adapters require their own future validated
routing contract; do not pretend that changing ignored terms searches a registry.
Existing operator tasks and candidates are preserved exactly. Generated additions
share the eight-candidate/eight-task/64-expanded-task limits, including retained
follow-up receipt capacity. Collection still shares six requests/45 seconds for
quick research and 24 requests/180 seconds for detailed research.

The planner has one attempt and a separate 20-second deadline. No retry or failure
fallback may expand source access or overwrite operator inputs. Unavailable or
invalid planning leaves the authorised original plan intact. Account revocation
and cancellation still prevent report persistence and release. No database locks
are held across model work.

## Receipts and selection

Freeze the planning policy, requested and returned model identity, outcome,
accepted proposals and bounded rejection explanation. Count planning separately
from translation and continuation. Server-created task origin and IDs distinguish
automatic tasks from operator instructions; request schemas cannot forge model
origin. Historical receipts without a planning trace retain their old encoding.

Attempted planning calls enter the run's in-memory usage totals, including on
cancellation. The existing pipeline persists usage on successful completion;
this is not durable billing accounting for cancelled or failed runs.

Actual executed supplementary terms must influence evidence ranking. Outstanding
accepted generated tasks must also participate in sufficiency checks. A model's
recommendation cannot silently skip them or turn an unsuccessful search into
confirmation. Final report coverage, analytical prompts and exported receipts
must describe the same accepted plan and task origins.

## Operator experience

The current plan preview remains deterministic and makes no model request. Explain
that an actual run may add bounded tasks within the selected sources and existing
collection budget. Preserve editing of operator hypotheses and tasks. Final
report details show exactly what was proposed, accepted and attempted, including
unavailable or rejected planning. Do not describe all supplementary tasks as
operator supplied after automatic planning is introduced.

## Acceptance

Focused backend acceptance passed 155 cases, including production collection,
ranking against newer unrelated records, selected-source admission, invented
direction-identifier refusal, deadline/cancellation accounting and exact legacy
JSON round trips. The first run had one incomplete gateway fixture and two
Windows parameter-name errors; repaired fixtures passed the complete focused
rerun. Strict mypy passed 571 source files, Ruff/format passed, both import
contracts passed and configured Bandit passed. Independent read-only review
found no unresolved actionable code or security findings.

Final full frontend acceptance passed 946 tests across 176 files. Coverage is
95.12% statements, 90.18% branches, 93.70% functions and 96.43% lines, meeting
the unchanged 90% gates. The first full run exposed a stale operator-origin
label assertion. The next passed all 935 tests but missed branch coverage at
89.58%; 11 additional behaviour tests cover missing metadata, source limitations,
personal overrides, invalid connection-test proofs and cancellation. They also
found and repaired a connection-test message being hidden by generic error
handling. Activation still requires valid successful test proof.

OpenAPI and generated TypeScript types were refreshed. Full frontend lint,
type checks, production build, file-length, UTF-8/LF and whitespace checks passed.
The existing large map-vendor build advisory remains. The first full backend
run reached 95.39% coverage with 3,048 passes, 24 skips and 11 failures. Tracebacks
identified asynchronous mocks for the synchronous planning port and historical
schema-0018 fixtures using the current personal-binding repository. The repaired
affected and planning group passed 189 cases, with nine optional PostgreSQL
cases skipped. Those nine then passed separately on PostgreSQL 17.10; all
disposable databases, the loopback-only container and volumes were removed.
No production change was needed for these fixture repairs. Repository hooks,
including Gitleaks, passed. Final full backend acceptance passed 3,059 tests
with 24 skips and 95.39% coverage in 2,455.56 seconds. One non-failing SQLite
ResourceWarning reported an unclosed connection; its allocation origin was not
identified by that run. No test failure remains in this acceptance run.
Logs: `data/automatic-planning-backend-acceptance.log`,
`data/automatic-planning-backend-full.log`, `data/model-planning-focused.log`,
`data/automatic-planning-frontend-acceptance.log`,
`data/automatic-planning-eslint-final.log` and `data/automatic-planning-build-final.log`.
The repair/PostgreSQL/hook logs are `data/model-planning-repaired-focused.log`,
`data/llm-provider-migration-postgres-acceptance.log` and
`data/automatic-planning-precommit.log`.

Required local cases include actual provider execution and evidence ranking,
operator preservation, selected-source enforcement, immutable temporal/AOI scope,
subject-adapter refusal, candidate/seed capacity, invalid identifiers, malformed
or oversized output, unavailable models, deadline/cancellation, authority changes,
sufficiency accounting, usage and historical receipt round trips. User interface
checks cover deterministic-preview disclosure and all final planning states.

Independent human review must separately evaluate negation, transliteration,
same-name entities, hypothesis relevance, unsupported severe allegations and
query meaning. Synthetic adversarial fixtures are engineering checks and cannot
supply the human-labelled benchmark required by E13.
