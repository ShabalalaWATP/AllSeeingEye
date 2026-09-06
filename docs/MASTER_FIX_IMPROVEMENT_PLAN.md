# Master fix and improvement plan

Status: local implementation complete, 6 September 2026. Baseline: `60dff6b`. This plan implements the
expanded request to reassess security, SOLID, documentation, maps, identity and
teams, exports, analytical quality and visual design. The earlier
[implementation plan](MASTER_IMPLEMENTATION_PLAN.md) remains the history of
Phases 0 to 6. Completion of those phases does not complete this broader goal.

## Findings at baseline `60dff6b`

The modular monolith, protocol ports, composition root, bounded live store and
test gates are worth keeping. Existing authentication is functional, with
Argon2id, rotating refresh tokens, CSRF, account approval and optional admin TOTP.
The app nevertheless needs substantive fixes, not just visual polish:

- Analytical validation accepts an empty response, accepts unverified model
  grades and applies a whole-pool confidence ceiling to individual judgements.
- Topic similarity can promote contradictory headlines to confirmed information.
  Copied reporting can also be counted as independent corroboration.
- Requested report periods can differ from the evidence-selection period;
  regenerated report-list metadata can retain the original dates.
- Only user/admin roles exist. Operational records and alert streams are shared
  across all signed-in users. There are no team privacy boundaries.
- Revoked refresh sessions do not immediately invalidate issued access tokens.
  Concurrent administrator changes lack a last-active-administrator invariant.
- Map choices already include satellite, hybrid and keyed OS variants, but hide
  unavailable OS choices and do not explain coverage or imagery age adequately.
- Exports work, but multilingual PDF handling, rendering verification and analyst
  presentation need further assessment. The doctrine document still mixes
  proposed capabilities with implemented facts.

These are evidence-backed findings from source review. Tests and review notes
must be updated as fixes land; a green test that encodes an incorrect expectation
is not proof of analytical correctness.

## Product and architecture decisions

Keep the 3D globe as the root, the actual Evil Eye brand, the current stack and
free feed/API sources. Raw live events remain bounded and transient. No paid
services, scraping, new cloud service, or unnecessary framework replacement.

Default team design: personal work is visible to its author and administrators;
team work is visible to current members of that team and administrators. Public
live feeds stay shared. Account role and membership determine authority together:
being a manager never grants global access. This policy is enforced across saved
work, background processing, exports, search and alert delivery.

| Capability | User | Manager | Administrator |
|---|---|---|---|
| Public live map and trackers | Read | Read | Read |
| Personal work | Own records | Own records | Administrative access |
| Team reports and requirements | Read assigned teams; manage own contributions | Manage teams explicitly assigned to lead | All teams |
| Team alerts | Read and acknowledge within scope | Same, plus team indicator/schedule oversight | All |
| Membership | View own team roster | Manage ordinary members of managed teams | Create teams, assign managers, manage memberships |
| Account approval, global roles, account reset links | No | No | Yes |
| Credentials, source configuration, global security audit | No | No | Yes |

Existing records retain IDs, authorship and frozen evidence. Do not guess team
membership or silently assign old records to a shared team. A migration must
inventory legacy cross-owner relationships and preserve provenance while refusing
new operations that cross the selected access boundary. No operator database is
migrated during development verification.

Visual thesis: a calm, precise intelligence workspace with the globe as the
dominant visual, dark surfaces, strong typography and restrained ember accents.
Content plan: purposeful sign-in; map workspace; contextual evidence inspector;
readable report workspace; separate account/team administration.
Interaction thesis: compact map disclosure, responsive contextual panels and
clear focus/state transitions. Honour reduced motion and hidden-tab behaviour;
do not add decorative dashboards, permanent ribbons or competing animations.

## Delivery and acceptance

### A. Analytical integrity and provenance

- [x] Strict validation at the new-model-response boundary while retaining reads
  of historical and failed report records.
- [x] Reject empty or unsupported assessments, unresolved references, ambiguous
  IDs and invalid confidence statements; derive grades from frozen evidence.
- [x] Assess confidence against each judgement's actual support.
- [x] Separate topic clustering from verified corroboration; handle copied and
  plainly contradictory reporting conservatively with honest explanations.
- [x] Match evidence selection to the requested reporting period and refresh
  saved current-period metadata on regeneration.
- [x] Assess translated-title selection, diversity, evidence gaps, assumptions,
  alternative explanations and changes between versions against real behaviour.
- [x] Regression tests demonstrate the defective behaviour before each fix;
  valid scripted reports and failed/legacy report reads remain supported.

### B. Identity, sessions and teams

- [x] Add user/manager/admin roles, explicit team memberships and audited team
  management, with manager authority limited to designated teams.
- [x] Add personal/team scope to operational roots and alerts. Enforce the same
  policy for list counts, direct reads, writes, exports, comparisons and search.
- [x] Validate every linked AOI/plan/report/indicator/schedule relationship.
- [x] Filter alert streams and revalidate membership while connected; recheck
  scope after model calls and before background work persists results.
- [x] Separate global embedding retention from caller-scoped search/indexing so
  one team's index operation cannot erase another team's vectors.
- [x] Reject old access tokens after logout and credential changes; protect the
  last active administrator under concurrent changes on SQLite and PostgreSQL.
- [x] Add usable account settings and role-aware team administration. Keep global
  account security and configuration restricted to administrators.
- [x] Clear scoped client caches and selections on identity/team changes.
- [x] Test cross-team identifier access on every route, escalation, membership
  revocation, background jobs, stream delivery and migration recovery.

### C. Maps and uncluttered visual design

- [x] Compact, keyboard-accessible selector for satellite, hybrid, OS Road,
  Outdoor and Light, plus useful keyless street/light/dark options.
- [x] Show coverage, provider attribution, imagery age and unavailable-key states
  honestly. Keep provider keys server-side and verify provider documentation.
- [x] Preserve projection, overlays, selected events and authentication through
  asynchronous style changes and failures.
- [x] Improve sign-in hierarchy, account assistance, password/code interaction
  and mobile layout without replacing the Evil Eye.
- [x] Review shell, globe, inspectors, reports and administration in a real
  browser at desktop and narrow widths; fix overflow and competing controls.
- [x] Verify keyboard/focus, loading/error/empty states, reduced motion and
  contrast, with no claim of a complete assistive-technology audit unless run.

### D. Export and analyst workflow quality

- [x] Review PDF, DOCX and Markdown with representative long and multilingual
  evidence; improve hierarchy, page flow, provenance and review status.
- [x] Preserve evidence hashes, capture times, source names, source grades and
  links in all formats. Never describe a snapshot as verified ground truth.
- [x] Make the reader distinguish observations, judgements, assumptions, gaps
  and alternative explanations clearly; carry that structure into exports.
- [x] Check exports from authorised historical versions and ensure revoked team
  membership cannot retrieve an export or search result.
- [x] Render and inspect representative documents where tools are available;
  record missing renderers or real-model evaluation as explicit outstanding work.

### E. Engineering, security and documentation closure

- [x] Keep business rules outside routes/components, split touched large files
  by responsibility, retain import contracts and generated API types.
- [x] Review outbound archive/webhook/tile boundaries and newly added access
  controls; fix validated defects with deterministic regressions.
- [x] Reconcile architecture, doctrine, feature inventory, operations and API
  documentation with implemented behaviour; record meaningful decisions in ADRs.
- [x] Run applicable SQLite/PostgreSQL tests, coverage gates, frontend tests,
  lint/types/import checks, builds, security tools and browser/document checks.
- [x] Perform a requirement-by-requirement final audit of this whole plan and
  the original objective. Keep uncertainty and operational gates explicit.
- [x] Commit coherent verified milestones. No push/hosted CI result is possible
  until a remote is configured; no production deployment is implied.

## Progress record

- 6 September: inspected clean baseline and opened `codex/app-improvement`.
  Completed focused read-only identity and analysis audits; map implementation
  and analytical-integrity regression work are in progress. The full goal remains
  active. Existing Phase 6 checks are baseline evidence, not verification of these
  new changes.

- 6 September, integrated implementation: strict analytical validation and conservative
  topic grouping, frozen translations and version dates, three roles and private team
  workspaces, guarded background work and streams, bounded private search, complete
  export provenance and responsive navigation/map/reader/team views are implemented.
  Independent reviews produced additional fixes for stale administrator decisions,
  sibling reset links, idle stream connections, scoped index retention, cache headers
  and export permission loss during rendering. Account self-service now includes
  own-password changes with current-password/factor checks and atomic session/link
  revocation. Final integrated verification is recorded below.
- External verification remains explicit: no real model endpoint has been exercised,
  OS Maps needs the operator's key, DOCX visual rendering needs an office renderer,
  and hosted CI cannot run without a remote. These do not justify inventing positive
  results or applying development migrations to the operator's data.

## Final audit and verification

The requested security, SOLID/code quality, documentation, map selection, accounts
and teams, exports, analytical integrity and visual improvements are implemented
and reviewed in sections A to E. The existing stack, root 3D globe, Evil Eye,
free sources and transient bounded live data remain intact. This is local
implementation completion, not approval for public exposure or an operator upgrade.

- SQLite: 673 tests passed, one PostgreSQL-only skip, 96.10 percent combined
  line/branch coverage. Three test connection warnings were traced to the session
  migration fixture, corrected, and five affected tests passed with resource
  warnings treated as errors.
- PostgreSQL 17: 675 tests passed. Separate synthetic migration round-trips
  preserved IDs, frozen evidence and readable audit records on both databases.
- Frontend: 351 tests passed in 74 files; 98.04 percent line and 91.95 percent
  branch coverage. Lint, both TypeScript projects, formatting and build passed.
- Ruff, mypy over 278 source files, both import contracts, file-size checks and
  pre-commit gates passed. Source Bandit, Semgrep, Gitleaks and dependency audits
  passed within their documented scopes.
- Desktop/mobile browser checks covered login, account, teams, globe and report
  evidence; representative PDFs were visually checked. DOCX structural checks
  passed, with visual rendering still unavailable on this host.
- Both container builds and the configured fixable HIGH/CRITICAL gate passed.
  The API has 54 unfixed package findings, including three CRITICAL matches;
  the web has none at those severities, including unfixed findings. Installed
  component/reachability evidence and release actions are in the
  [base image triage](security/API_BASE_IMAGE_TRIAGE.md). No vulnerability ignores
  or operator risk acceptance were added.
- The improvement is committed on `codex/app-improvement`; no remote, hosted CI,
  operator migration or deployment is included. Use the operations guide before
  upgrading an installation, and retain the matching encryption key and backup.
