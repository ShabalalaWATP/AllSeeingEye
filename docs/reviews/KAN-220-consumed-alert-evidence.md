# KAN-220: consumed alert evidence beyond the citation cap

Worktree: `kan-220-consumed-alert-evidence`, branch
`codex/KAN-220-consumed-alert-evidence`. Base: `bc507cd2`.
The primary shared instructions and this worktree's `CLAUDE.md`, development
workflow and parallel policy apply. Jira acceptance criteria were read live from
KAN-220; the coordinator owns the claim and external publication.

## Behaviour and boundaries

- A 22-match alert still counts 22 and cites 20. All 22 identities are committed
  with the alert and notification intents, so uncited matches cannot trigger a
  second alert after cooldown or restart.
- Identity state is independent of event publication ordering. Two previously
  unseen older late arrivals can satisfy a threshold of two. Rule edits retain
  consumption through the maximum seven-day window, including its lower edge.
- Relative baselines retain complete hourly counts. Full and previously
  unconsumed counts come from one admitted immutable snapshot. A relative firing
  additionally needs its threshold of new matching identities.
- Each rule has its own record and the same owner/team/current-revision checks
  protect reads and writes. Capacity accounting, consumption, alert persistence
  and notification enqueue share the existing cross-process administration guard
  and transaction. Cancellation or failure before commit rolls everything back.
- Records use a strict versioned binary format: 16-byte SHA-256 prefixes of
  length-delimited source/ID values plus 8-byte exact UTC microsecond expiries.
  The 128-bit collision risk is negligible, not mathematically zero. No event
  content or raw identity text is persisted. Parsing and encoding run off-loop.
- Limits are 350,000 identities per rule and 1,000,000 globally. Default retained
  category caps total about 313,000, including 150,000 disasters; a 10,000-item
  cap would regress legitimate existing rules and the 10,037-match regression.
  Overflow defers the entire firing with a named operational reason. It never
  evicts eligible records or records partial consumption.

## Migration and compatibility

Migration 0094 follows the coordinator's 0093 reservation. Existing alerts and
reports remain unchanged. Old citation samples cannot reconstruct all consumed
IDs, so old alerted rules receive an explicit legacy firing boundary. Ambiguous
activity at or before it is deferred and diagnosed while still eligible. This
one-time limitation includes older late arrivals; post-boundary arrivals work.
A deliberate pause/resume can establish a fresh publication boundary.

The nullable legacy boundary is retained across edits, but no warning is emitted
when the active window or resume boundary already excludes it. Expiry removes it.
New-version restarts use complete saved state. Database downgrade refuses any
retained consumption. Application rollback requires stopping warning workers,
because an older binary cannot honour the new deduplication contract. No actual
operator database, configuration or running service was changed.

## Validation evidence

The initial two regressions failed against the base: after cooldown the absolute
rule repeated the two uncited matches; the relative rule repeated all 22. Both
passed after the change, including evaluator restart and older late arrivals.
The expanded group exposed SQLite's disabled foreign-key cascade; rule deletion
now explicitly removes its state, and the follow-up passes.

- Final focused group: 145 tests passed across 18 relevant files. Combined measured
  coverage for the consumed-state, warning persistence, evaluator and warning-domain
  modules was 90.70% (the repository's 90% gate was retained). The new codec measured
  97%, the new consumption adapter 91%, and warning-domain evaluation 100%.
- Checks passed: Ruff and formatting for all 19 changed Python files, strict mypy
  across 1,602 source files, Bandit on changed production modules, all three import
  architecture contracts, `git diff --check`, and the 350-line source target.
- An independent read-only code/security reviewer traced bounds, expiry, current
  revision/scope checks, administration locking, atomic commit, corruption refusal,
  restart/lost acknowledgement, relative-mode validation and legacy migration.
  No actionable findings remained. The reviewer did not execute tests.
- Real independent SQLite connections verified that concurrent rules cannot exceed
  global capacity, and a reopened on-disk database retained consumption after a
  committed transaction whose acknowledgement was lost.

The focused suite used isolated synthetic fixtures with shared database variables
cleared. PostgreSQL and the full repository coverage suite were not run here.
Migration-chain verification follows integration of the coordinator's committed
0092/0093 predecessors. Full repository CI and release approval remain with the
coordinator. There are no frontend, package or generated API changes and no live
provider calls.
