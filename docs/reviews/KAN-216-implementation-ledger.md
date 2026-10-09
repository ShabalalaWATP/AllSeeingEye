# 9 October review: implementation and acceptance ledger

This is the integration record for Alex's instruction to implement every reviewed
ticket. Jira remains the delivery tracker. The reviewed starting revision is
`13efceef48efbc6d5f2895e60c55076db5d40e3f`, including Claude's latest merged
KAN-215 change. The remote was rechecked on 10 October and still named that
revision. The primary checkout and its uncommitted contributor changes remain
untouched; implementation uses isolated ticket branches and worktrees.

The integration branch is `codex/KAN-216-review-integration`. It combines the
reviewed branches without merging to `main`. Several draft PRs include their
prerequisites, so PR counts must not be summed as independent changes or test
totals. Focused test groups overlap. A local passing check does not imply that
CI, native PostgreSQL, browser acceptance or deployment has completed.

## Ticket coverage

| Ticket | Implementation | Review artefact / remaining acceptance |
| --- | --- | --- |
| KAN-164 | Neutral offer wording and a concrete software-licence/offer decision record | PR #175; Alex's licence and offer decision required |
| KAN-165 | Public privacy, storage, attribution and data-request pages; fail-closed publication gate | Integrated source; public browser acceptance and operator/legal approval pending |
| KAN-166 | Bounded opt-in enquiry admission, atomic duplicates, operator-only email | PR #184; full CI/native PostgreSQL pending |
| KAN-167 | Administrator enquiry API, session fences, bounded retention and erasure | PR #185; full CI/native PostgreSQL pending |
| KAN-168 | Public enquiry form, enabled-only sign-in links, contact focus | Integrated source; combined public browser acceptance pending |
| KAN-169 | Administrator enquiry workspace, actions, focus and pagination | 31 focused tests passed; scoped coverage/native browser acceptance pending |
| KAN-172 | Public route isolation, search metadata, robots policy and bundle budget | Integrated source; combined public browser/performance acceptance pending |
| KAN-182 | Server-owned idle expiry, genuine activity, warning and stale-tab protection | PR #183; full CI/native PostgreSQL pending |
| KAN-184 | Explicit per-provider external embed consent, local preferences | PR #178; preview heading regression corrected, final style recheck pending |
| KAN-194 | Source licence evidence, attribution catalogue and permission-request drafts | PR #180; provider permissions are not inferred or sent |
| KAN-195 | Commercial-use admission and capability controls | Independent review repairs and combined regressions in progress |
| KAN-206 | Brief remount synchronisation and valid globe fixtures | PR #181; focused follow-ups passed, final CI pending |
| KAN-217 | Durable bounded alert-report queue | PR #171; historical migration fixtures repaired, final CI pending |
| KAN-218 | Frozen exact rule scope and triggering evidence | PR #176; final CI pending |
| KAN-219 | Executable alert template requirements and legacy recovery | PR #179; earlier geometry and migration fixtures repaired, final CI pending |
| KAN-220 | Complete consumed-evidence persistence, atomic caps and restart safety | PR #186; full CI/native PostgreSQL pending |
| KAN-221 | Exact saved report/version links, including unavailable historical targets | PR #177; FK-valid SQLite/PostgreSQL follow-up passed, final CI pending |
| KAN-222 | Unsaved Brief navigation protection | PR #168; remount follow-up integrated, final CI pending |
| KAN-223 | Unique indicator identifiers after removal/re-addition | PR #169 |
| KAN-224 | Honest unsupported private-input choices in canonical Briefs | PR #172; remount follow-up integrated, final CI pending |
| KAN-225 | Concrete GitHub production approval proposal and no-op gate check | PR #163; live environment approval required |
| KAN-226 | Uncached security rebuild procedure | PR #170 |
| KAN-227 | Vulnerable dependency and image refresh | PR #164; local rebuilt-image scan and CI passed |
| KAN-228 | Explicit webhook retry semantics after uncertain acceptance | PR #174 |
| KAN-229 | Safe name/recurrence edits preserving pinned scope and history | PR #182; 64 backend and 34 UI cases passed, final CI pending |
| KAN-230 | CI security and acceptance documentation reconciled with executable gates | PR #173 |
| KAN-231 | Bounded synthetic-data Chromium CI journeys | Source review complete with one selector repair; runtime/representative PR pending |
| KAN-232 | Responsibility splits, extended size gate and reviewed exceptions | PR #187; final combined inventory pending |
| KAN-233 | Authentication before saved-map bodies and bounded admission | PR #165 |
| KAN-234 | Request/refresh binding to the originating login | PR #166; final integrated CI pending |
| KAN-235 | Original TLS identity across pinned feed connections; no shared cookies | PR #167 |
| KAN-236 | Same-session fences throughout semantic search | PR #162 |

PR numbers refer to `ShabalalaWATP/AllSeeingEye`. Per-ticket review files retain
exact local commands, measurements, failures, repairs and scope limitations.

## Review findings corrected during implementation

- Public-enquiry admission initially escaped an outer SQLite rollback through a
  first-write savepoint. A direct dialect-specific conflict insert now remains in
  the caller's transaction; failure and independent-connection tests passed.
- Conditional idle expiry originally risked revoking a family kept active in
  another tab. The server now confirms the named family's current deadline and
  does not clear a replacement cookie.
- Administrator enquiry pagination lost success feedback/focus after deleting
  the final row. Stable workspace feedback and post-modal focus ownership retain
  both across the page transition.
- Nullable historical subscription options initially escaped the conditional
  edit comparison. SQL/JSON-null regressions now pass.
- The public sign-in contact link initially changed the fragment without moving
  to the lazy-loaded form. Scoped fragment scrolling and heading focus are added.
- PostgreSQL rejected two edition-link fixtures before testing projection.
  FK-valid mismatch fixtures and real-SQL missing-reference projections now pass
  on SQLite and a disposable instance of CI's pinned PostgreSQL image.
- Commercial-policy review found private-upload and conflict-reference consumers
  bypassing their declared policies. Their repairs must be independently
  re-reviewed before this workstream is accepted.

## Approval and release boundaries

No production release, live migration or merge to `main` is authorised by this
implementation request. Migration revisions0090 through0094 form one chain;
operator rollout and data-preserving rollback limitations require the documented
manual migration process.

The public notice still needs the actual controller identity/contact details,
applicable geography, lawful-basis wording and approval. The existing approved
operator-assisted data-request contact is retained only for that stated purpose.
The licence/offer decision and live GitHub production-environment configuration
also require Alex's explicit decision. The publication gate remains closed;
feature flags default to disabled. Provider permission drafts have not been sent,
and commercial permission has not been assumed.

The 6 October KAN-81 acceptance remains historical evidence. This review adds a
continuous browser lane and does not retroactively change its recorded outcome.
