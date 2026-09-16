# ADR 0019: Durable AI allowance admission and settlement

Status: accepted for the teams, profiles and AI usage slice

Date: 15 September 2026

## Context

The existing `llm_usage` table is a provider call audit trail. It is written after a
model request and therefore cannot prevent a user or team from exceeding an
administrator-defined allowance. Report jobs also have a separate, job-local budget.
The new team model needs a site-wide policy that can cover personal and explicit team
work without holding a database transaction open while a provider is called.

## Decision

Add a separate policy and ledger bounded by three calendar periods: day, week and
month. Policies can target the site (`global`), shared unattended work (`system`), one
user or one team. A policy has independent request and token ceilings. `None` means
unlimited; zero is an explicit deny-all ceiling and is never interpreted as unlimited.

### Admission and settlement

Admission creates one reservation row per applicable policy in its own transaction,
grouped by a `call_id`. The counter row is updated with a conditional relative SQL
`UPDATE`, so concurrent reservations cannot both pass a finite ceiling. Dispatch is
recorded in a second short transaction immediately before the provider request; if it
cannot be recorded the call is not sent. The provider call then happens without an
open database transaction. Every later counter change is also a relative conditional
`UPDATE`; rows are touched in a deterministic order (the call's reservations, then
counters by policy id, then the totals row), so workers cannot overwrite each other's
increments or deadlock.

The gateway decorators wrap the provider gateway directly and classify each outcome:

| Outcome | Reservation | Counters |
| --- | --- | --- |
| Exception before the provider request (cancellation while reserving or recording dispatch) | `released` | reservation returned; no request, no tokens |
| Provider answered | `settled` | one request; reported prompt plus completion tokens, or the reserved amount when a completed call reports no counts |
| Provider error (including token budget exhaustion) | `settled` | one request; only the tokens the error reported, usually zero |
| Timeout or cancellation after dispatch | `unknown` | reservation held; not released and not resent |

Reconciliation runs opportunistically during admission, at most once a minute per
process, in a bounded batch of 20 calls. A reservation still `reserved` after one hour
(`STALE_RESERVATION_AGE`) is released when dispatch was never recorded and marked
`unknown` when it was, keeping the charge conservative. The administrator preview
reports the number of calls held as unknown. There is no automatic release of unknown
calls; an explicit review action is future work.

### Retention

The ledger keeps only what admission, reconciliation and the current views need. The same
opportunistic admission path prunes expired rows, at most once an hour per process, in
one short transaction that is never held across a model call. Each table loses at most
500 rows per run through a single `DELETE ... WHERE key IN (SELECT key ... LIMIT 500)`,
which behaves the same on SQLite and PostgreSQL. When any table fills its batch the next
run follows at the one-minute reconciliation pace until the backlog clears. A failure is
logged by exception type only and never blocks admission; a successful run logs the
number of rows removed per table and no account or team identifiers.

| Rows | Removed when | Never removed |
| --- | --- | --- |
| `ai_usage_reservations` | status `released` or `settled` and `period_end` more than 90 days ago (`RESERVATION_RETENTION`) | `reserved` (in flight or awaiting reconciliation) and `unknown` (awaiting review) |
| `ai_usage_counters` | `period_end` more than 400 days ago (`PERIOD_RETENTION`, about 13 months) | any counter still carrying a reserved request or token |
| `ai_usage_totals` | `period_end` more than 400 days ago | none beyond the age rule |

Allowance summaries (`/api/ai-usage/me`, the administrator preview and team usage views)
read only the counter and totals rows for the current period, and the preview's
`unknown_calls` counts only `unknown` reservations, so pruning never changes a figure a
user or administrator sees. The administrator reservation listing shows the latest 100
rows and simply stops showing expired ones. Migration `0054` adds a
`(status, period_end)` index on reservations for the selection; counters and totals stay
small (one row per policy period and per monthly attribution bucket) and are selected
without an extra index. The provider audit trail in `llm_usage` is unaffected.

In the durable report job path the allowance decorator sits inside the job's
`ReportCallBudget`, so a job refusal never reserves allowance, and an allowance refusal
is recorded in the job ledger as `not_dispatched` and does not consume the job's output
budget. The monthly owner and subscription ceilings in `monthly_report_usage.py` remain
a separate admission check and are not charged twice in this ledger.

### Attribution and observation

Global and user policies apply to personal work. A team policy applies only when the
caller supplies an explicit team destination for which the account is a current member
or an active site administrator; otherwise the call is attributed to the account alone.
This prevents a personal Ask Eye question from consuming the allowance of every team the
account joins, and prevents an arbitrary team identifier from charging, or exhausting,
another team's allowance. System work is charged to the global and system policies.

Usage is always recorded, with or without a policy. `ai_usage_totals` keeps one monthly
row per system bucket, per account and per account within a team, so observation mode
has bounded storage and managers can see member totals. Reservation rows are written
only when a policy applies. Members see only their own attributed team usage, team
Managers see the team aggregate and member totals, and administrators can view any team
through `GET /api/teams/{id}/ai-usage` without membership.

### Temporary overrides

`ai_usage_policy_overrides` holds dated overrides of a policy with `effective_from` and
`expires_at` (at most 366 days, at most ten open per policy). Each limit states
`inherit`, `limit` (a whole number, where zero blocks), `unlimited` or `blocked`. The most
recently created override active at the time of admission replaces the base limits.
Revocation is recorded rather than deleting the row. Creation, revocation and admission
serialise on the same policy row lock, and creation and revocation are audited.

Policy deletion remains a revisioned disable operation so reservations stay auditable
within their retention window. Provider assignment and encrypted credentials remain in the existing
model-routing implementation.

## Model call inventory

Verified on 15 September 2026 against `backend/src/ase`. "Covered" means the provider
call passes through an allowance decorator.

| Path | Provider call | Attribution | Covered |
| --- | --- | --- | --- |
| Ask Eye map questions | `application/assistant/model.py` via `MapAssistant._answer` | Actor, personal | Yes |
| Ask Eye report Q&A | same | Actor, plus the report's team when the edition is team-owned | Yes |
| Interactive report generation and regeneration (all stages, automatic claims) | `reports/production.py` `_metered_gateway` | Report actor and request team | Yes |
| Indicator alert reports | same interactive path | Indicator owner and team | Yes |
| Durable report jobs: subscriptions, schedules, daily, economy and cyber briefings | `container/report_job_gateways.py` | Stored job owner and team (subscription editions carry the subscription owner and team); one reservation per call, no second wrapper | Yes |
| Native web search, interactive and jobs | `reports/fresh_web_research.py`, `_RoutedWebGateway` | Report actor and team | Yes |
| Photo geolocation | `research/photo_model.py` | Actor and optional team | Yes |
| Manual claim generation | `reports/generate_claims.py` | Requesting account and the report's team | Yes |
| Semantic report search, index and query embeddings | `reports/search.py` | Actor, personal (the index spans all visible reports) | Yes |
| Administrator connection test, completion and embeddings probes | `admin/llm_testing.py` | The administrator running the test | Yes |
| Feed title translation | `adapters/llm/translator.py`, built in `container/features.py` | System | Yes |
| Conflict screening of shared feeds | `application/conflict_screening/model.py` | System | Yes |
| Economy page plain-English explainer | `application/economy_explainer_model.py`, built in `container/economy_explainer.py` | System, purpose `economy_explainer` | Yes |
| Model discovery (`list_models`) | `adapters/llm/openai_compatible.py` | Not a completion; lists models only | No, not billable model usage |
| Fortnightly Ukraine digest | `application/ukraine_digest_writer.py`, built in `container/ukraine.py` | System, purpose `system:ukraine_digest`; at most one call a fortnight, plus one retry when the mechanical checks reject the first answer | Yes |

Tests cover each newly metered path except conflict screening, which uses the same
`system_llm_gateway()` wiring as feed translation but has no dedicated allowance test.
The economy explainer has its own allowance test
(`tests/test_economy_explainer.py::test_the_call_is_reserved_and_settled_against_the_system_budget`)
asserting a settled reservation, system attribution and the exact purpose string. It
passes `purpose_prefix=""` to `AllowanceLlmGateway`, which records the schema name
alone rather than a prefixed purpose; it is the only consumer that does so. Its
cadence is at most one call per fact-pack fingerprint and never more than once in 24
hours, with a single retry when the mechanical checks reject an answer, so it can
spend at most two calls a day. See `docs/ECONOMY_WORKSPACE.md`.

## Consequences

The admission path is fail-closed when an enabled policy is exhausted and reports a
stable `ai_usage_limit` error. Feed translation leaves titles untried when the system
allowance is exhausted and retries on its normal interval rather than busy looping.
Reservation rows grow per metered call while policies exist, but finished rows are pruned
90 days after their period ends and counters and totals after about 13 months, so the
ledger stays a small operational aggregate. Pruning is admission-driven: an instance
that makes no metered calls also prunes nothing, which is acceptable because only
admission adds rows. Only timeouts are
treated as unknown after dispatch; a transport error after the request was written is
counted as a failed request with zero tokens. The PostgreSQL lock ordering is verified by
design and by the SQLite concurrency tests; the suite has no disposable PostgreSQL run
recorded for this change.
