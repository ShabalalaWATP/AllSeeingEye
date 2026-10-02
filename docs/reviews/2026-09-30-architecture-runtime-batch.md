# Architecture and runtime batch, 30 September 2026

Branch: `codex/KAN-6-architecture-batch`, based on `69696286c45a905937f666f4056768c6f8087475`.
The implementation used the managed `kan6-architecture-batch` worktree, its own
Python environment and temporary SQLite databases. Instructions were read from
`C:/AlexDev/OSINT/AGENTS.md`, `CLAUDE.md`, `docs/DEVELOPMENT_WORKFLOW.md` and
`docs/PARALLEL_DEVELOPMENT.md` before editing. Alex explicitly requested the
remaining Codex backlog in batches of about eight, overriding the earlier
single-item queue preference. No production resources or credentials were used.

## Delivered code scope

| Jira | Result |
| --- | --- |
| KAN-6 | Report production delegates preparation/resumption, drafting/accounting and challenge/advocacy to named stages. `Producer` retains its public signatures and no statement-count suppression. All touched production files remain below 350 lines. |
| KAN-7 | Application services own subscription publication, lineage/comparison/delivery policy, retry classification and the waiting/pause/recovery state machines. Narrow transaction ports expose SQL adapters using the caller's existing session. Container modules only wire and delegate. |
| KAN-8 | The container constructor calls named initialisers. Research service and connector assembly move into `container/feed_services.py`, preserving construction order, explicit connector overrides, credentials and watchlist inclusion. |
| KAN-9 | Typed annotation resolver lookup dispatches claim, identity and relationship anchors/revisions through public service methods. Missing optional capabilities fail with a controlled unavailable-kind error. Scope and frozen evidence validation remain inside the existing services. |
| KAN-11 | `FeedScheduler` composes `FeedPoller`, delegating direct polls, breaker reset, health access and pruning. Scheduling retains jitter, stagger, retry deadlines and cancellation cleanup. |
| KAN-12 | `ChallengeExpansionMixin` is abstract and requires `_read` and `mutate`. A negative mypy probe rejects an incomplete concrete implementation. |
| KAN-13 | All fourteen container casts have local rationales. No shared members were added speculatively to `ContainerCore`. |
| KAN-44 | CLI commands import application wiring and optional dataset implementations only when needed. Structured `startup.phase` events carry `duration_ms` for import, container, snapshot restore, worker startup and readiness. |

## Validation

- Baseline report snapshots/checkpoints/budget and scheduler selection: 96 passed.
  An earlier harness invocation incorrectly set the optional test database URL
  to an empty string, causing six setup errors; removing the variable restored
  the private in-memory SQLite default.
- Report production, challenge, reranking, continuation, budget and checkpoint
  selection after extraction: 224 passed.
- Broader subscription, annotation monitor/export and feed selection: 341
  passed, 17 PostgreSQL skips, four outdated test patch targets failed. Those
  test references were relocated with the extracted SQL adapter. The repaired
  recovery/pause suites were included in a subsequent 53-test passing run
  alongside new annotation/retry contracts and targeted selection coverage.
- CLI, application lifespan and Ukraine import command selection: 44 passed.
- Final migration import and designation command selection: 13 passed.
- `mypy src`: passes for 1,382 modules. Ruff check and format check pass.
  Import-linter retains all three contracts. File-length and whitespace checks
  pass; none of the touched source or test files exceeds 350 lines.
- Repository-configured Bandit (`uv run bandit -q -c pyproject.toml -r src`):
  passes. An initial invocation without the repository config reported 24
  B101/B105 low-severity findings, which the existing policy explicitly skips.
- `MYPYPATH=src uv run mypy <temporary incomplete expansion subclass>` fails
  specifically with both missing abstract methods, as intended.
- Actual `python -X importtime` execution of `ase migrate` against a disposable
  SQLite database imports 175 `ase` modules, below the ticket's 200-module
  limit. A subprocess regression also rejects application, feed and model
  wiring on that path. Import-only `ase.cli` changed from 1,354 modules to
  106 after the first lazy-import slice; later command deferral reduces it
  further. Observed 13.12 s versus 4.24 s import durations were under shared
  development-host load and are not controlled performance evidence.

Coverage was not measured for these focused `--no-cov` runs. The repository's
full coverage gate and CI remain required before release. PostgreSQL concurrency
acceptance is blocked by the unavailable local Docker engine and lack of an
isolated PostgreSQL database. No shared database was used. KAN-44's reference-host
SIGTERM-to-first-successful-ready reduction of at least three seconds remains
unverified and must not be marked complete from module counts or local timings.

## Review notes and integration boundaries

The publication and retry extractions preserve policy statement order. Report,
job, edition, comparison, lineage and delivery writes remain in the original
publication transaction. Retry admission takes the source guard before the
administration guard, retains job/edition revision compare-and-set operations
and rolls back when either fence fails. Resumption never resolves unknown paid
usage. Model-call sequencing and usage updates remain beside their existing
operations; a resumed collection retains its frozen selection and skips the
embedding call. Startup timing logs contain only fixed phase names and numeric
durations. These are implementation review notes, not independent approval.

Concurrent branches need deliberate integration at these boundaries:

- Pool configuration arguments belong in `Container._initialise_database()`.
- New UN/EU snapshot settings belong in `feed_services.build_research_service()`.
- The encryption rotation CLI registration must retain lazy implementation imports.
- Notification outbox hooks must remain commit-free in the publication/retry
  SQL transaction adapters. Publication and retry wrapper public signatures
  are preserved; moved policy helpers now live under `application/schedules`.
- Lifecycle health/shutdown instrumentation can wrap the existing worker calls;
  preserve the timing points around snapshot restoration and completed startup.
- Scheduler progress instrumentation belongs in its existing connector/prune
  loops. Tests needing single-poll internals now address `scheduler.poller`.

No push, pull request, merge, deployment or Jira transition was performed by
this implementation worker. Publication, independent review and release approval
remain with the coordinating task.

## Coordinator integration

Published as draft PR #89 on top of the workflow/contracts PR #88. The first
SQLite and PostgreSQL CI runs exposed an incomplete test container in the
expired-lease recovery regression. It now provides the retry service's real
default monthly policy and an isolated source guard. All 22 tests in that
regression module pass locally; Ruff, formatting and whitespace checks pass.
The updated PostgreSQL CI run remains required. This fixture repair does not
relax the application's retry or lease fences.
