# Forecast and alert feedback: KAN-125 to KAN-129

Updated 1 October 2026. Branch: `codex/KAN-125-forecast-feedback`.
Integrated parent: `e3ef726ea57885100f3331924ada7e876c4e6b3a`, performance PR #93,
including main `9ae40e3d` and its alert-rule, bell, citation and team-copy workflows.
This batch is a draft for review;
release, email delivery and research accuracy require their own evidence.

## Delivered behaviour

| Ticket | Change and acceptance evidence |
| --- | --- |
| KAN-125 | The report reader creates forecasts from exact reviewed claims and frozen passage references. Reviews require explicit outcomes and later same-scope reviewed evidence. Corrections and replacements append history; a single ordinal compare-and-swap protects replacements. Scoped watches distinguish review dates from outcome horizons, record deduplicated in-app receipts, and allow selected JSON history exports. |
| KAN-126 | Outcome counts filter personal/team scope before aggregation and count each forecast version's latest decision under its original PHIA band. True and false alone form the denominator. Open, due, unresolved and superseded counts remain separate; no probability midpoint, percentage or accuracy score is inferred. |
| KAN-127 | Ratio rules use retained hourly samples, a positive historical mean and at least 168 sampled hours spanning seven days. Absolute thresholds and cooldowns remain. Semantic edits reset samples transactionally and stale in-flight samples fail the current-rule check. Fired alerts retain the count, mean and ratio. |
| KAN-128 | Ask Eye explains an authorised alert using only bounded retained references, with matched/sample/available counts. Empty context returns before model routing. Current source, session and alert access are rechecked after generation and at HTTP release. There is no global fallback or unrestricted continuation. |
| KAN-129 | The first shared acknowledgement may include useful/noise/duplicate and a bounded plain-text note. Daily per-rule disposition counts survive raw-alert pruning while retaining current scope checks. Feedback does not change firing or cooldown. |

Email digest delivery is supplied by the following notifications batch, using
`forecast_digest.due_review_count(session, visibility, since, until)`. The helper
uses current versions, a half-open review-date interval, current recipient scope
without an administrator override, and an explicit truncation flag. This batch's
in-app reminders work independently of email configuration.

## Integration boundaries

The parent provides all-kind 30-day baseline retention and the activity hour/ID
index. The evaluator retains both its worker-health wrapper and the new rule
sampler. This batch now uses `0084` after parent `0083`, then `0085` and `0086`.
The resulting graph has one head, `0086`. These replace the unpublished revision
identifiers `0069`, `0070` and `0073`; the shipped main chain through `0081` is
unchanged. An installation already at `0081` therefore executes every new revision.

The API schema and TypeScript contracts are regenerated from the combined source.
The PostgreSQL SQL-rendering check starts at `0083` because the parent's earlier
checkpoint reconciliation requires actual database reads. SQLite tests execute
the combined chain and check existing alert preservation, feedback downgrade
refusal and reminder-table round trips.

## Current main compatibility checks

The rule update path retains main's optimistic revision guard and scope-widening
confirmation. Baseline samples reset only after its conditional write succeeds,
inside the same transaction. Pause/resume retains the ratio configuration and
`resumed_at` excludes paused activity. The bell treats a conflict as one failed
item and retains successful acknowledgements; the first shared acknowledgement
still owns any feedback. The UI preserves mine/all views, other-owner confirmation,
rule drafts, ratio settings, frozen alert explanations and saved forecasts.

Report composition retains team-copy provenance, map links and citation verdicts.
Citation verdicts do not review a proposed claim or rewrite an issued forecast.
Copying a personal report to a team preserves its evidence timestamps, but creates
no claim roots, forecast ledgers or reminder receipts in the destination scope.

The combined source passed 256 backend cases in three non-overlapping groups
(32, 150 and 74), using private in-memory or temporary SQLite databases and
`--no-cov`. This includes actual `0084`–`0086` migrations, retained-history downgrade
refusals, conditional-write loss and rollback, pause/resume sampling, bell partial
failure, exact claim binding, late alert-access rechecks and historical `0030`
metadata projection. The warning and report-reader groups passed 100 frontend
tests across 20 files using MSW and Node 24.19.0. Two existing exact request-body
assertions were extended for `baseline_ratio: null` and `baseline_days: 30`; their
previous assertions remain. No coverage thresholds changed. A final 23-case ratio, edit, pause and report-draft
rerun passed after removing type-redundant form fallbacks.

Both frozen dependency installs and OpenAPI/client regeneration succeeded. Full
mypy passed for 1,502 source files, both TypeScript projects passed, full Ruff and
formatting passed for 2,644 Python files, all three import contracts held and the
file-length gate passed. Full frontend lint (including eight tooling tests) and a
second check of both TypeScript projects also passed. The targeted warning/bell Bandit scan reported no
medium/high findings. Changed frontend files pass Prettier. The full frontend
format check still reports 12 files with no Git diff from parent `e3ef726e`;
these are recorded for the parent-wide integration rather than reformatted in this
feature batch. These focused checks do not measure combined coverage; that remains
part of the parent-coordinated integration gate.

Independent final read-only review found no actionable issues in the combined
rule, bell, router and container composition. All 322 parent OpenAPI operations
remain (328 total); current ownership, revision and scope-widening checks survive.
The final rule state/reset and retained-context implementations match the reviewed
candidate. Feature-commit Gitleaks scans reported no leaks.

## Security review

An independent reviewer examined exact claim/excerpt binding, scoped counts,
replacement concurrency, archived-team reminder writes, baseline resets and
retained alert context. The review reproduced a late membership-revocation gap
in the final alert source check. The repair orders the application source check
before final authorisation and retains the HTTP administration guard through the
last alert and session checks. Two regression phases revoke membership during
the application and transport source checks; the independent reproduction also
passed after the fix. No additional actionable findings remained in that review.

Acknowledgements retain the existing active team-member write contract. Archived
team writes remain restricted, with the existing administrator manual override
preserved where applicable. Neither aggregate counts nor exports widen scope.
Targeted Bandit inspection of nine affected modules reported no medium/high
findings. Gitleaks 8.24.3 scanned all seven non-merge feature commits in
`d72c9237..HEAD` with redaction enabled and reported no leaks. These targeted
checks are not an exhaustive repository security scan.

A subsequent independent migration review found that `0070` originally guarded
only configured ratio rules. Historical snapshots could therefore be discarded
after the rule changed or disappeared. Six new edited/deleted-rule cases first
failed against that implementation. The repair also refuses when either alert
baseline field is non-null, before any DDL. Regression snapshots compare the
complete SQLite schema, data and revision before and after refusal; configured
rules and safe empty downgrade remain covered.

Historical `0030`/`0031` migration tests now compare an explicit cloned metadata
projection excluding only the four alert fields introduced in `0069`/`0070`.
Live ORM metadata and the existing current migration tests are unchanged.
The combined ratio, historical SQLite, feedback and reminder migration group
passed all 23 tests after the repair (89.94 seconds, `--no-cov`); changed-file Ruff
and formatting passed. Independent read-only review found no further gap.

An independent private PostgreSQL rehearsal passed all six combined upgrade,
preservation, constraints and downgrade-guard tests plus all five historical
inventory tests. The expanded run initially found one remaining duplicate `0030`
metadata projection in the PostgreSQL monitor test. That test now reuses
`metadata_0030()`; its targeted real PostgreSQL rerun passed (one test, 4.49 seconds),
joining the 16 other passing cases. The reviewer verified disposal of all generated
databases and its labelled container. No production database was involved.

## Validation and limits

Local checks use the worktree's private Python environment, node_modules, scratch
SQLite databases, fake providers and MSW. No production database, real model or
mail provider was used. The earlier checks below used Node 22.20.0; the current
main compatibility checks above use supported Node 24.19.0.

Full mypy passed for 1,425 source files; full TypeScript checking, Ruff, all three
import contracts, changed frontend ESLint checks and the file-length gate passed.
Eight frontend test files passed all 31 tests. The production build and bundle
gate passed with seven initial JavaScript chunks totalling 196,659 gzip bytes.
The combined backend regression run passed all 188 tests in 82.57 seconds
with `--no-cov` against parent `909eabab`. It covers forecast lifecycle/counts/scope/exports, retained ledger
validation, alert feedback and ratios, all three new migrations, parent performance
storage/migrations, runtime health, assistant application/API/report/alert context,
session-fence architecture and warning admission/backpressure/background access.
The parent CI repairs and refreshed session-fence exemptions are included.
After merging final parent `2290b8c0`, 18 stream-shutdown, alert-context and
session-fence regressions passed; full mypy and TypeScript checks passed again.
After the repaired parent `447227b4`, a further 23 focused stream-pool/shutdown,
alert-context, release-fence and performance-storage tests passed in 13.28 seconds.
That parent adds no API schema changes.

Coverage was not measured in these focused checks. Full CI/coverage, browser acceptance and notification pipeline integration remain
separate release evidence. The later dependency parent changes only the audited
lockfile and CI evidence document; its owner validated frozen installation, zero
audit vulnerabilities, API generation, focused tests, lint, build and bundle checks. Deterministic tests do
not establish model quality, production latency or forecast calibration.

Feature guides: [Forecast reviews](../FORECAST_REVIEWS.md) and
[alert feedback](../ALERT_FEEDBACK.md).
