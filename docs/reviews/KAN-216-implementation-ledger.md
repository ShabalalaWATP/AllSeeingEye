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
| KAN-165 | Public privacy, storage, attribution and data-request pages; fail-closed publication gate | Grouped PR #191; public policy browser checks passed; operator/legal approval required |
| KAN-166 | Bounded opt-in enquiry admission, atomic duplicates, operator-only email | PR #184; full CI/native PostgreSQL pending |
| KAN-167 | Administrator enquiry API, session fences, bounded retention and erasure | PR #185; focused SQLite/native PostgreSQL retention checks passed; full CI shards pending |
| KAN-168 | Public enquiry form, enabled-only sign-in links, contact focus | Grouped PR #191; final functional mobile browser and contact-focus checks passed; CI pending |
| KAN-169 | Administrator enquiry workspace, actions, focus and pagination | PR #189; browser reflow/focus repairs verified; 17 acceptance tests passed with 94.64% scoped branch coverage |
| KAN-172 | Public route isolation, search metadata, robots policy and bundle budget | Grouped PR #191; full-page mobile Lighthouse 78/97/100, desktop 99/97/100; mobile performance remains below the earlier placeholder-stage 95 criterion |
| KAN-182 | Server-owned idle expiry, genuine activity, warning and stale-tab protection | PR #183; final CI identified uncovered backend auth refusal branches and dependent PostgreSQL logout/concurrency failures; repairs in progress with original assertions and the 95% security floor unchanged |
| KAN-184 | Explicit per-provider external embed consent, local preferences | PR #178; preview heading regression corrected, CI passed at `5eedf1d8`, In Review |
| KAN-194 | Source licence evidence, attribution catalogue and permission-request drafts | PR #180; provider permissions are not inferred or sent |
| KAN-195 | Commercial-use admission and capability controls | PR #188; retained-source repair independently reviewed, 168 affected cases passed with 96.44% scoped coverage; final readiness/contrast repair at `dc5e0565` passed 55 frontend cases; CI pending |
| KAN-206 | Brief remount synchronisation and valid globe fixtures | PR #181; CI passed, In Review |
| KAN-217 | Durable bounded alert-report queue | PR #171; historical migration fixtures repaired, CI passed, In Review |
| KAN-218 | Frozen exact rule scope and triggering evidence | PR #176; CI passed, In Review |
| KAN-219 | Executable alert template requirements and legacy recovery | PR #179; geometry and migration fixtures repaired, CI passed, In Review |
| KAN-220 | Complete consumed-evidence persistence, atomic caps and restart safety | PR #186; full CI/native PostgreSQL pending |
| KAN-221 | Exact saved report/version links, including unavailable historical targets | PR #177; FK-valid SQLite/PostgreSQL follow-up passed, CI passed at `be35567b`, In Review |
| KAN-222 | Unsaved Brief navigation protection | PR #168; remount follow-up integrated, CI passed, In Review |
| KAN-223 | Unique indicator identifiers after removal/re-addition | PR #169 |
| KAN-224 | Honest unsupported private-input choices in canonical Briefs | PR #172; remount follow-up integrated, CI passed, In Review |
| KAN-225 | Concrete GitHub production approval proposal and no-op gate check | PR #163; live environment approval required |
| KAN-226 | Uncached security rebuild procedure | PR #170 |
| KAN-227 | Vulnerable dependency and image refresh | PR #164; local rebuilt-image scan and CI passed |
| KAN-228 | Explicit webhook retry semantics after uncertain acceptance | PR #174 |
| KAN-229 | Safe name/recurrence edits preserving pinned scope and history | PR #182; 64 backend and 34 UI cases passed; obsolete disabled-edit test repaired with 11 focused cases; fresh CI pending |
| KAN-230 | CI security and acceptance documentation reconciled with executable gates | PR #173 |
| KAN-231 | Bounded synthetic-data Chromium CI journeys | PR #190; four local journeys passed in 11.354 seconds and hosted CI in 9.9 seconds (64-second full job); final aggregate pending |
| KAN-232 | Responsibility splits, extended size gate and reviewed exceptions | PR #187; 13 reviewed target exceptions, no hard-limit failure; startup import regression repaired, fresh CI pending |
| KAN-233 | Authentication before saved-map bodies and bounded admission | PR #165 |
| KAN-234 | Request/refresh binding to the originating login | PR #166; MFA refresh regression repaired the coverage gap, CI passed at `dcc5b737`, In Review |
| KAN-235 | Original TLS identity across pinned feed connections; no shared cookies | PR #167 |
| KAN-236 | Same-session fences throughout semantic search | PR #162 |

PR numbers refer to `ShabalalaWATP/AllSeeingEye`. Per-ticket review files retain
exact local commands, measurements, failures, repairs and scope limitations.

## Combined verification

At `c87b652f`, 168 selected backend cases passed across commercial policy,
retained/private inputs, maps, subscription edits, exact edition links, enquiry
administration and migration boundaries. Whole-source mypy passed for 1,637
files; Ruff and formatting passed for 2,940 files, and all three import contracts
passed. Combined API export and TypeScript generation left no contract diff.
Public credits were regenerated for the added Ordnance Survey Maps policy, and
both attribution tests passed. Both TypeScript configurations passed.

Four additional real-adapter alert cases at `ce5a3387` verify current commercial
permission before admission and before queued execution. Denial produces the
expected safe error without model calls or a report; exact-source permission
permits normal completion. Independent review of this positive/negative matrix
passed. These focused results do not replace full combined CI.

After the retained-source repair and browser-lane merge, 53 affected backend
cases passed together. Whole-source mypy passed for 1,638 files, Ruff passed,
frozen frontend installation and both TypeScript configurations passed, and all
11 public-policy checks passed. The migration CLI's 204-module regression was
separately reproduced and repaired by loading infrastructure adapters only for
their selected commands; the unchanged budget passes at 196 modules, with 26
focused CLI/migration tests. The combined branch subsequently passed 46 cases
covering that unchanged startup budget, the complete 96-owner/359-route contract,
upload session checks, release-time expiry and transactional token redemption.
The shared fixtures now model activity deadlines explicitly, preserving expiry,
rollback and single-use assertions. Independent review of the branch-specific
route inventories found no dropped contract checks.

Queued cookie-only logout now has explicit stable-cookie and replaced-cookie
controls. All 77 auth-store tests passed with 97.14% branch coverage against the
unchanged 95% floor. Enquiry retention passed 17 SQLite and 17 native PostgreSQL
cases, and 12 lifecycle cases verify the configured retention reaches housekeeping.
Map-policy integration reproduced 12 outdated readiness/contrast failures; all
55 affected cases now pass, with the original loading/denied/cancellation
assertions retained. The only additional production change in that follow-up is
the existing accessible border token on the basemap selector.

At integrated revision `26ef4c4b`, all 32 ticket implementations and their reviewed
follow-ups are present. The production build and all four isolated Chromium
journeys passed (13.8 seconds), covering the combined commercial, enquiry,
session, subscription and notification changes. The pinned browser was installed
into this worktree through the repository's own installer. The final route,
public-page, administrator, graphics and auth group passed 235 tests in 37 files.
Both TypeScript configurations and all 11 policy checks passed. API and attribution
regeneration left no diff. The expanded size check passed with 13 documented
target exceptions and no hard-limit failure.

Whole frontend lint also passed. Whole-tree formatting exposed 11 files already
outside the current formatter's style at the reviewed baseline. A separate
KAN-232 formatting commit reconciles them; independent review found no code
semantics changed, and all three JSON values were compared with their original
parsed data. Whole-tree formatting now passes.

Final gzip bundle measurements passed their unchanged budgets: initial loading
145,738 of 245,760 bytes, globe additions 829,227 of 870,400 bytes, and public
product additions 44,427 of 153,600 bytes. Final combined hosted CI remains pending.
At this checkpoint, 18 delivery tickets have passing current-head CI and are In
Review. Ten require final validation or CI repair, and four retain acceptance or
operator decisions. No delivery ticket has been marked Done.

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
  bypassing their declared policies. Their repairs passed independent review.
  Combined review then found retained public corroboration and direct reuse
  gaps. A shared source collector now enforces every retained primary and folded
  source before fresh work; red/green tests and independent review passed.
- Mobile browser checks found long enquiry contacts overflowing implicit grid
  tracks and long organisation names overflowing deletion dialogs. Explicit
  mobile tracks and text wrapping pass the same geometry checks after repair.
- Session changes made the cyber-filter API test depend on browser cookies; its
  previous Node-only classification was corrected, with all ten focused tests
  passing and the fix propagated to dependent branches.
- Chromium found the notification menu behind report content and a focus race
  when acknowledged or muted rows disappeared. Header stacking and commit-bound
  focus restoration now pass actual browser clicks and a delayed-refresh test.

## Approval and release boundaries

No production release, live migration or merge to `main` is authorised by this
implementation request. Migration revisions 0090 through 0094 form one chain;
operator rollout and data-preserving rollback limitations require the documented
manual migration process.

The public notice still needs the actual controller identity/contact details,
applicable geography, lawful-basis wording and approval. The existing approved
operator-assisted data-request contact is retained only for that stated purpose.
The licence/offer decision and live GitHub production-environment configuration
also require Alex's explicit decision. The publication gate remains closed;
feature flags default to disabled. Provider permission drafts have not been sent,
and commercial permission has not been assumed.

The completed animated public page measures 78 performance, 97 accessibility and
100 SEO on default mobile Lighthouse, and 99/97/100 on desktop. The mobile baseline
was 60/97/100; host benchmark variation is recorded in the acceptance evidence.
KAN-172's earlier 95-performance criterion specified placeholder chapters. The
full-page result remains below that figure and has not been waived or presented
as passing. Further renderer work or an explicit acceptance decision is outstanding.

The 6 October KAN-81 acceptance remains historical evidence. This review adds a
continuous browser lane and does not retroactively change its recorded outcome.
