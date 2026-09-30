# Forecast and alert feedback: KAN-125 to KAN-129

Recorded 30 September 2026. Branch: `codex/KAN-125-forecast-feedback`.
Integrated parent: `d72c9237b644fbb6d3276c6eb890d08989ffa8fd`, performance PR #93.
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
sampler. Migration `0069` follows `0068`, then `0070` follows `0069` and `0073`
follows `0070`. The resulting graph has one head, `0073`.

The API schema and TypeScript contracts are regenerated from the combined source.
The PostgreSQL SQL-rendering check starts at `0068` because the parent's earlier
checkpoint reconciliation requires actual database reads. SQLite tests execute
the combined chain and check existing alert preservation, feedback downgrade
refusal and reminder-table round trips.

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
mail provider was used. Frontend checks used Node 22.20.0, which reports the
repository's Node >=22.22.0 engine warning; runtime verification must use the
supported version before release.

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
