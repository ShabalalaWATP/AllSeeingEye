# Codex backlog delivery, 30 September 2026

Jira is authoritative for acceptance and status. Alex requested the remaining
Codex backlog in PRs of around eight related tickets. This explicitly expands
the initial ready queue and allows grouped PRs. Smaller feature groups keep
substantial related work reviewable. Ticket count is not an effort estimate.

## Verified baseline

- Fetched `origin/main`: `69696286c45a905937f666f4056768c6f8087475`.
- No open GitHub PRs at the initial preflight.
- Jira returned 63 non-epic tickets and 12 coordinating epics assigned to Codex
  outside Done, including three already implemented tickets.
- KAN-146, KAN-148 and KAN-147 were reconciled to Done after verification of
  merged [PR #81](https://github.com/ShabalalaWATP/AllSeeingEye/pull/81),
  commit `d1455d7b`, successful final CI and recorded independent reviews.
  This does not assert live deployment/provider validation.
- The primary checkout's uncommitted workflow/history edits were preserved.
  Each batch starts in a separate managed worktree with private dependencies
  and test outputs. Prepared primary-checkout instruction files were read
  before work began.

## Batch register

The register covers 58 implementation and documentation tickets in nine batches,
plus two operator-only prerequisites. Each delivery record maps ticket criteria
to actual checks, unresolved acceptance and a PR. Review status does not mean
acceptance or release is complete.

| Batch                            | Tickets                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Branch                                |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| Workflow, contracts and guidance | [KAN-2](https://alex-orr.atlassian.net/browse/KAN-2), [KAN-4](https://alex-orr.atlassian.net/browse/KAN-4), [KAN-22](https://alex-orr.atlassian.net/browse/KAN-22), [KAN-23](https://alex-orr.atlassian.net/browse/KAN-23), [KAN-143](https://alex-orr.atlassian.net/browse/KAN-143), [KAN-144](https://alex-orr.atlassian.net/browse/KAN-144)                                                                                                                       | `codex/KAN-4-backlog-delivery`        |
| Backend performance              | [KAN-28](https://alex-orr.atlassian.net/browse/KAN-28), [KAN-31](https://alex-orr.atlassian.net/browse/KAN-31), [KAN-33](https://alex-orr.atlassian.net/browse/KAN-33), [KAN-34](https://alex-orr.atlassian.net/browse/KAN-34), [KAN-35](https://alex-orr.atlassian.net/browse/KAN-35), [KAN-37](https://alex-orr.atlassian.net/browse/KAN-37), [KAN-38](https://alex-orr.atlassian.net/browse/KAN-38), [KAN-39](https://alex-orr.atlassian.net/browse/KAN-39)       | `codex/KAN-28-performance-batch`      |
| CI and test quality              | [KAN-69](https://alex-orr.atlassian.net/browse/KAN-69), [KAN-70](https://alex-orr.atlassian.net/browse/KAN-70), [KAN-71](https://alex-orr.atlassian.net/browse/KAN-71), [KAN-72](https://alex-orr.atlassian.net/browse/KAN-72), [KAN-73](https://alex-orr.atlassian.net/browse/KAN-73), [KAN-74](https://alex-orr.atlassian.net/browse/KAN-74), [KAN-75](https://alex-orr.atlassian.net/browse/KAN-75), [KAN-76](https://alex-orr.atlassian.net/browse/KAN-76)       | `codex/KAN-69-ci-test-batch`          |
| Security and operations          | [KAN-16](https://alex-orr.atlassian.net/browse/KAN-16), [KAN-17](https://alex-orr.atlassian.net/browse/KAN-17), [KAN-18](https://alex-orr.atlassian.net/browse/KAN-18), [KAN-19](https://alex-orr.atlassian.net/browse/KAN-19), [KAN-21](https://alex-orr.atlassian.net/browse/KAN-21), [KAN-153](https://alex-orr.atlassian.net/browse/KAN-153), [KAN-154](https://alex-orr.atlassian.net/browse/KAN-154), [KAN-155](https://alex-orr.atlassian.net/browse/KAN-155) | `codex/KAN-153-security-operations`   |
| Architecture and startup         | [KAN-6](https://alex-orr.atlassian.net/browse/KAN-6), [KAN-7](https://alex-orr.atlassian.net/browse/KAN-7), [KAN-8](https://alex-orr.atlassian.net/browse/KAN-8), [KAN-9](https://alex-orr.atlassian.net/browse/KAN-9), [KAN-11](https://alex-orr.atlassian.net/browse/KAN-11), [KAN-12](https://alex-orr.atlassian.net/browse/KAN-12), [KAN-13](https://alex-orr.atlassian.net/browse/KAN-13), [KAN-44](https://alex-orr.atlassian.net/browse/KAN-44)               | `codex/KAN-6-architecture-batch`      |
| Sources and exports              | [KAN-130](https://alex-orr.atlassian.net/browse/KAN-130), [KAN-131](https://alex-orr.atlassian.net/browse/KAN-131), [KAN-132](https://alex-orr.atlassian.net/browse/KAN-132), [KAN-133](https://alex-orr.atlassian.net/browse/KAN-133), [KAN-134](https://alex-orr.atlassian.net/browse/KAN-134), [KAN-139](https://alex-orr.atlassian.net/browse/KAN-139), [KAN-140](https://alex-orr.atlassian.net/browse/KAN-140)                                                 | `codex/KAN-130-sources-exports`       |
| Opt-in notifications             | [KAN-110](https://alex-orr.atlassian.net/browse/KAN-110), [KAN-111](https://alex-orr.atlassian.net/browse/KAN-111), [KAN-112](https://alex-orr.atlassian.net/browse/KAN-112), [KAN-113](https://alex-orr.atlassian.net/browse/KAN-113), [KAN-141](https://alex-orr.atlassian.net/browse/KAN-141)                                                                                                                                                                     | `codex/KAN-110-notification-delivery` |
| Forecasts and alert feedback     | [KAN-125](https://alex-orr.atlassian.net/browse/KAN-125), [KAN-126](https://alex-orr.atlassian.net/browse/KAN-126), [KAN-127](https://alex-orr.atlassian.net/browse/KAN-127), [KAN-128](https://alex-orr.atlassian.net/browse/KAN-128), [KAN-129](https://alex-orr.atlassian.net/browse/KAN-129)                                                                                                                                                                     | `codex/KAN-125-forecast-feedback`     |
| Runtime observability            | [KAN-41](https://alex-orr.atlassian.net/browse/KAN-41), [KAN-42](https://alex-orr.atlassian.net/browse/KAN-42), [KAN-43](https://alex-orr.atlassian.net/browse/KAN-43)                                                                                                                                                                                                                                                                                               | `codex/KAN-41-runtime-observability`  |
| Operator-only prerequisites      | [KAN-45](https://alex-orr.atlassian.net/browse/KAN-45), [KAN-46](https://alex-orr.atlassian.net/browse/KAN-46)                                                                                                                                                                                                                                                                                                                                                       | `No implementation branch`            |

## Published review stack

The live Jira recheck on 30 September returns 60 open non-epic tickets:
54 in review, four in progress and two to do. Twelve coordinating epics also
remain open. These counts include published work awaiting acceptance and release.

All nine PRs are published as drafts. Their bases follow this order; an approved
merge must be followed by updating and checking the next affected branch against
the resulting main. The primary checkout's prepared edits remain untouched.

| Order | PR                                                           | Batch                            | Tickets |
| ----- | ------------------------------------------------------------ | -------------------------------- | ------- |
| 1     | [#88](https://github.com/ShabalalaWATP/AllSeeingEye/pull/88) | Workflow, contracts and guidance | 6       |
| 2     | [#89](https://github.com/ShabalalaWATP/AllSeeingEye/pull/89) | Architecture and startup         | 8       |
| 3     | [#90](https://github.com/ShabalalaWATP/AllSeeingEye/pull/90) | Runtime observability            | 3       |
| 4     | [#91](https://github.com/ShabalalaWATP/AllSeeingEye/pull/91) | CI and test quality              | 8       |
| 5     | [#92](https://github.com/ShabalalaWATP/AllSeeingEye/pull/92) | Security and operations          | 8       |
| 6     | [#93](https://github.com/ShabalalaWATP/AllSeeingEye/pull/93) | Backend performance              | 8       |
| 7     | [#94](https://github.com/ShabalalaWATP/AllSeeingEye/pull/94) | Forecasts and alert feedback     | 5       |
| 8     | [#95](https://github.com/ShabalalaWATP/AllSeeingEye/pull/95) | Sources and exports              | 7       |
| 9     | [#96](https://github.com/ShabalalaWATP/AllSeeingEye/pull/96) | Opt-in notifications             | 5       |

The first three PRs passed their complete CI at the published implementation
heads. Later branches are undergoing combined checks and repairs. Fresh Linux
evidence establishes 94% combined backend coverage, 92.16% frontend branches,
the reviewed 95% security/auth floors and a 70% floor for frontend files with at
least 20 branches. These are dated measurements, not an assertion that every
subsequent feature branch has completed its own checks.

The first successful selected PostgreSQL CI run executed 2,361 unique cases with
no omission from the reviewed 2,360-case census. Its 62.1 runner-minutes exceeded
KAN-71's 30-minute target, so timing optimisation and measurement remain active.
The corrected controlled DOM/Node comparison passed the same 3,644 cases with
identical coverage, saving 59.11 seconds against KAN-73's 70-second requirement.
Twenty more isolated files passed focused Node checks; a new controlled pair
remains necessary. The incomplete archive and unmatched-cache observations are
excluded from acceptance.

The complete CI run `36664614145` passed at the CI batch's `57d202a5` checkpoint.
Subsequent shard discovery at `cccfa79f` uses one test root and an explicit ignore
list, retaining the exact selected cases. Its local collection comparison fell
from 70.44 to 11.72 seconds for the same 572 cases. All eight PostgreSQL collection
partitions contain 2,363 unique cases with no omissions, including two additional
rotation-isolation guards. Root verification passed 13 runner tests and ten
isolation tests. This is collection evidence, not the runner-minute acceptance.

Combined PR #96 run `36665421330` passed every PostgreSQL shard, image builds and
security audits. It failed three backend fixture groups, frontend control-border
assertions, merged frontend branch coverage (91.75%) and a construction-only Atom
XML import finding. Those failures remain active repairs; the 92% global and 70%
per-file coverage requirements remain unchanged.

The complete notification integration passed 211 SQLite backend cases and 40
frontend cases. Three PostgreSQL concurrency cases passed separately. The
[combined migration rehearsal](../reviews/2026-09-30-combined-migration-rehearsal.md)
passed six new PostgreSQL cases and the repaired historical checks, preserving
legacy data, private sender receipts and frozen alert evidence. It records the
exact failed-then-repaired fixture sequence and verified resource cleanup.

## Shared contracts and integration

The coordinator owns this register and the master plan/development story.
Workers own their batch's code and dedicated evidence record. Shared changes
remain narrow: container factories, settings, lifecycle hooks, CLI registration,
generated OpenAPI and client types. Each PR must work against its own base.
Later PRs require updating from the resulting reviewed main and rerunning
combined checks. No branch may erase another batch's changes.

The integrated migration chain is `0066 -> 0067 -> 0068 -> 0069 -> 0070 -> 0073
-> 0071 -> 0072 -> 0074`. Forecast reminders precede notification digests even
though their reserved numbers are not in numerical order. Migration 0067 has an
intentional privacy downgrade guard; historical roundtrip tests must not bypass
it. The combined database rehearsal is linked above. Never deploy a combined set
with accidental multiple heads.

Keep the required CI check identities. Run focused tests independently and
coordinate full coverage/performance runs to avoid invalid timing evidence.
Do not lower coverage thresholds. Real SMTP, model calls, production databases
and operator credentials are excluded from software verification.

## Explicit external acceptance

- KAN-45 needs the approved SSH destination, monitoring recipient/service,
  retention and cost choices, then approved live configuration and an isolated
  recovery from the off-host copy. Existing helper tests cannot satisfy this.
- KAN-46 requires the operator to replace and revoke three provider keys and
  verify production use without copying key values into chat or tickets.
- KAN-22 private vulnerability reporting was enabled and read back as enabled
  through GitHub. A private report was not submitted; recipient notification
  delivery is not yet verified.
- KAN-23's operator-assisted policy and shared-team retention stance need the
  operator's choice. Documented limitations must not imply account-wide erasure.
- KAN-131 requires a real 24-hour translation measurement. Source probes and
  deterministic tests cannot substitute for this elapsed workload evidence.
- Isolated Compose, PostgreSQL and browser checks now provide local evidence:
  catalogue gzip/conditional requests were exercised through real Caddy and Edge;
  100,000 public events survived a clean shutdown and restart; key rotation and
  publication transactions passed on fresh private PostgreSQL databases. These
  checks do not establish production readiness or live provider acceptance.
- KAN-134 needs the installation's HAPI identifier and live response validation.
  UN/EU import approval and NVD terms review remain explicit source prerequisites.
- KAN-110/111 request a manual SMTP check when operator configuration is available.
  Current installation SMTP availability has not been established. KAN-113 requires
  a manual Android Chrome check; an iOS device check is recommended when supporting
  that platform. KAN-112 does not require a live relay/webhook check, and KAN-141 does
  not require a real feed-reader check. Reader, webhook and iOS deployment checks
  must not become additional Jira closure criteria. Offline tests do not prove
  live delivery.
- The four-week dependency-update observation requires elapsed operations.
- KAN-2's Jira Development field now reports one GitHub draft pull request after
  PR #88 was opened. This was read from Jira's cached integration metadata,
  beyond merely putting a Jira key in a branch/PR name.

All new implementation tickets remain open until their checks, independent
reviews, acceptance criteria and authorised merge are complete. Epics remain
open while their children do. Opening a PR is not production release approval.

## Historical delivery snapshot, 1 October 2026

This section supersedes the earlier current-status counts, CI conclusions and
migration reservations; their dated evidence remains historical. At that checkpoint Jira had
**68 open Codex items: 57 non-epic delivery/prerequisite items and 11 coordinating
epics**. KAN-1, KAN-2, KAN-4 and KAN-144 are Done following their recorded verification.
The earlier KAN-146/KAN-148/KAN-147 reconciliation remains unchanged. The remaining
57 comprise 55 batched items and the two operator prerequisites, KAN-45/KAN-46.
Implemented, reviewed and CI-passing work is not automatically Done or released.

Main is `9ae40e3d`. The primary checkout at `9a01161a` and the user's prepared edits
remain untouched. The review stack continues from PR88 through PR96; no merge to
main or production deployment is authorised by this register.

| PR                                                          | Checked head                  | Latest full workflow named **CI**                                                                          |
| ----------------------------------------------------------- | ----------------------------- | ---------------------------------------------------------------------------------------------------------- |
| [88](https://github.com/ShabalalaWATP/AllSeeingEye/pull/88) | `9634f824`                    | [36922277772](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36922277772), passed              |
| [89](https://github.com/ShabalalaWATP/AllSeeingEye/pull/89) | `fad1327f`                    | [36923838968](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36923838968), passed              |
| [90](https://github.com/ShabalalaWATP/AllSeeingEye/pull/90) | `f1a32e17`                    | [36927813271](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36927813271), passed              |
| [91](https://github.com/ShabalalaWATP/AllSeeingEye/pull/91) | `18ce8245`                    | [36930619530](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36930619530), passed, all 30 jobs |
| [92](https://github.com/ShabalalaWATP/AllSeeingEye/pull/92) | `6886a141`                    | [36931665034](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36931665034), passed              |
| [93](https://github.com/ShabalalaWATP/AllSeeingEye/pull/93) | `2afb4831`                    | [36931692903](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36931692903), passed              |
| [94](https://github.com/ShabalalaWATP/AllSeeingEye/pull/94) | `2097eb3b`                    | [36933344519](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36933344519), pending             |
| [95](https://github.com/ShabalalaWATP/AllSeeingEye/pull/95) | `a45ae032`                    | [36933445271](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36933445271), pending             |
| [96](https://github.com/ShabalalaWATP/AllSeeingEye/pull/96) | `68af50a1` working checkpoint | Final source checks and independent reviews passed; full published-head CI required                        |

PR91's current frontend evidence records 4,292 tests, one skip and **92.14% branch
coverage**. Its passing CI supersedes the earlier failed main-integration diagnostic;
it does not certify downstream feature heads. PR95's
[36931922889](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36931922889)
passed the separate two-job **Image SBOMs** workflow, not full CI. Required CI
identities and the existing global, per-file and security/auth floors remain intact.

### Reconciled migration chain

After main's untouched `0081`, the combined chain is:

`0081 -> 0082 -> 0083 -> 0084 -> 0085 -> 0086 -> 0087 -> 0088 -> 0089`

| Revision | Feature                     |
| -------- | --------------------------- |
| `0082`   | Invitation privacy receipts |
| `0083`   | Performance projections     |
| `0084`   | Alert feedback              |
| `0085`   | Frozen indicator ratios     |
| `0086`   | Forecast reminders          |
| `0087`   | Notification delivery       |
| `0088`   | Alert routing               |
| `0089`   | Browser push                |

Only previously unmerged Codex migrations were rekeyed. Main's historical chain,
including `0075` following `0066`, remains unchanged. The privacy and frozen-evidence
downgrade refusals remain deliberate. See the
[migration reconciliation](../reviews/2026-10-01-migration-history-reconciliation.md)
for real SQLite/PostgreSQL history checks and their limits. Final PR96 whole-model parity and 21 real history cases pass on SQLite/PostgreSQL. Published-head CI remains required; isolated historical
rehearsals do not authorise production migration or rollback.

### Remaining acceptance and release work

- Finish PR96 integration, inspect the pending full CI runs and complete any resulting
  repairs. Record reviews and checks against the final immutable heads, then obtain
  authorised stack-merge/release decisions. Recheck downstream branches after each
  parent change. Green CI alone does not close every ticket criterion.
- Retain criterion-specific measurement requirements: KAN-69/KAN-71 comparable
  multi-run timing evidence; KAN-70's twenty consecutive main runs; KAN-73's controlled
  70-second saving with coverage difference within 0.05 percentage points; and KAN-75's
  repeatability and four weekly dependency-update observations. Historical partial
  improvements and the new coverage result are not substitutes for those criteria.
- KAN-45 still needs approved off-host backup/monitoring choices and an isolated
  recovery from that copy. KAN-46 needs operator replacement/revocation of the three
  provider keys and verification of production use. No key values belong in tickets.
- KAN-22's reporting setting is verified, but private-report recipient delivery is
  unverified. KAN-23 still needs the operator's policy/shared-team retention decision;
  deactivation and supported record deletion must not be called account-wide erasure.
- KAN-130 needs authority-specific UN/EU access/reuse approval before enabling imports;
  KAN-131 needs the genuine 24-hour translation measurement; KAN-134 needs the
  installation's HAPI identifier and live response-row validation. KAN-133's official
  NVD terms/rate review and non-endorsement notice are now verified and implemented,
  so they are no longer an outstanding prerequisite.
- Acceptance clarification, 2 October 2026: KAN-110/111 manual relay validation is
  conditional on operator configuration and remains unperformed; current installation
  SMTP availability is unknown. KAN-113 still requires manual Android Chrome
  validation. An iOS device check is a recommended platform release check. Real
  feed-reader and relay/webhook checks are operational recommendations, not additional
  KAN-141 or KAN-112 closure criteria. Fixture transports and disposable databases do
  not prove inbox, device or production delivery. Other batch-specific operator and
  production observations remain governed by their delivery records.

Jira remains authoritative. The count of 57 non-epic items belongs to the dated
checkpoint above. Keep individual items open wherever checks, review, acceptance
or authorised release are still outstanding.

## Approved release checkpoint, 2 October 2026, 09:23 UTC

Alex approved serial squash merges of PRs #88 through #96. Each next branch is
integrated with released main through an ordinary merge and checked again before
release. The primary checkout and its prepared changes remain untouched.

| PR                                                          | Verified merge | Fresh full PR CI                                                                              |
| ----------------------------------------------------------- | -------------- | --------------------------------------------------------------------------------------------- |
| [88](https://github.com/ShabalalaWATP/AllSeeingEye/pull/88) | `1d924272`     | [36922277772](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36922277772), passed |
| [89](https://github.com/ShabalalaWATP/AllSeeingEye/pull/89) | `d1a0c2dc`     | [36978951307](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36978951307), passed |
| [90](https://github.com/ShabalalaWATP/AllSeeingEye/pull/90) | `09397750`     | [36980735468](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36980735468), passed |
| [91](https://github.com/ShabalalaWATP/AllSeeingEye/pull/91) | `339477b7`     | [36982635004](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36982635004), passed |

Main CI on `339477b7` also passed. KAN-143, KAN-6/7/8/9/11/12/13,
KAN-41/42 and KAN-72/74/76 moved to Done with verified Jira transition responses.
Epics KAN-5 and KAN-142 closed after all their children and outcomes were verified.
The live Jira reconciliation returned **44 unfinished delivery tickets and nine
open epics**. This is a timestamped count, not a substitute for the live queue.

PR #92's final proxy-fixture repair is `428798b0`. Its real-Caddy and cleanup
validation passed 22 isolated Linux cases plus eight local helper cases, and both
independent review rechecks were clear. CodeQL analysed that exact head with zero
findings and marked alert 5038 fixed; its review thread is resolved. Full CI
[36989072603](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36989072603)
is still running. PRs #92 through #96 have not merged at this checkpoint.

The genuine KAN-131 feed audit began at 08:05:53 UTC on 2 October against frozen
source `a45ae032`. Three observation rounds have completed with zero feed failures
and zero automatic translation attempts. Its earliest full 24-hour acceptance is
after 08:05:53 UTC on 3 October, subject to the final evidence checks. KAN-70's
bounded twenty-run main CI observer is prepared but will start only after the
final approved-stack main-push CI passes on a stable revision. KAN-71/73 performance
follow-up remains in progress; partial timing gains do not meet their acceptance.

Production endpoint secret names and timestamps were verified. The existing
deployment key and host pin were preserved. The protected VPS controller requires
its private manual rollout procedure for migration and Compose changes, so no
successful production deployment is claimed. Installation-specific data policy,
off-site backup choices, provider-key rotation, source permissions and device or
configured-mail acceptance remain governed by their actual Jira criteria.

## Approved release checkpoint, 2 October 2026, 10:48 UTC

PRs #92, #93 and #94 have now also merged with approval, respectively as
`137a15a8`, `3026e936` and `fdf45607`. Their fresh full PR CI runs
`36991257642`, `36993285749` and `36995441810` passed. Main CI after #92
passed, and the main-push API and web CycloneDX SBOM inventories both succeeded
on that exact revision.

KAN-17/18/19/21/43/153/154/155, KAN-31/33/34/35/37/38/39 and
KAN-125/126/127/128/129 are verified Done. Epic KAN-106 closed after all five
children and its functional constraints were verified. The live queue at this
checkpoint contains 24 unfinished delivery tickets and eight open epics.

PR #95 is integrated at `da38f161`; full CI `36997213683` is still running.
PR #96 is locally integrated with released main, with its notification test
settings preserved. Neither PR has merged at this checkpoint. The native feed
audit has completed six rounds with zero failures or automatic translations;
its full 24-hour criterion remains pending. The CI performance follow-up has a
controlled full-suite Node improvement of 88.0644 seconds and a bounded
PostgreSQL mechanism improvement of 28.63 percent. Whole-CI timing acceptance
and the follow-up release remain outstanding.

## After approved PR #95 release, 2 October 2026

PR #95 merged as `20739857` after full CI `36998795486` passed on
`b05c0097`. All four CodeQL analyses reported zero findings. The two synthetic
URL-dispatch findings were fixed by exact URL/hostname test matching; all review
threads are resolved. Both image SBOM jobs passed. KAN-132, KAN-133, KAN-139
and KAN-140 are verified Done. The reconciled queue now contains 20 unfinished
delivery tickets and eight open epics.

PR #96 integrated this actual release at `cb1d4093`. Its production source,
generated contracts, migrations, configuration and lockfiles remain identical
to its reviewed final source. The final integration adds only the two verified
test repairs and review documentation. A fresh full CI run is required before
its approved release; no PR #96 merge or successful production rollout is
claimed here.

Draft PR #121's first full CI `36997668645` passed. Its PostgreSQL whole-job
measurement was 53.7 runner-minutes, exceeding KAN-71's target of under 30.
Further fixture/schema profiling is required. The passing full frontend CI
retained 92.14 percent branch coverage and all configured floors. KAN-73's
controlled Node timing improvement remains 88.0644 seconds; its follow-up
release is outstanding. KAN-70's twenty-run observer has not started, and the
KAN-131 full 24-hour audit and other operator criteria remain open.

## Final approved stack release, 2 October 2026, 11:40 UTC

PR #96 merged as `13e9525d904e744e0bc7ea329e8d475234f86f25` at
11:40:35 UTC after its exact-head full CI `37000486784`, four CodeQL analyses
and both image SBOM jobs passed. All nine approved original PRs, #88 through
#96, are now merged. The coordinator's reconciled queue contains **18 unfinished
delivery tickets and seven open epics**. Individual elapsed observations,
operator criteria and follow-up performance acceptance remain open.

Draft PR #121 integrates this released main through a normal merge. Its first
whole PostgreSQL measurement remains 53.7 runner-minutes against the required
under-30 target; the later local reflection and coverage-reporting work is not
whole-CI acceptance. KAN-73's controlled 88.0644-second frontend improvement is
retained, with the follow-up release still requiring current CI, review and
approval. No successful production rollout is claimed by these merges.

## Follow-up acceptance checkpoint, 2 October 2026

The coordinator's verified reconciliation now contains **16 unfinished delivery
tickets and seven open epics**. KAN-110 and KAN-111 are Done: their software,
automated checks, independent reviews and approved release are complete. Their
Jira criteria make manual SMTP/relay checks conditional on operator configuration.
Those manual checks remain unperformed until a configured relay is available;
this does not establish production SMTP status or successful real delivery.

Draft [PR #121](https://github.com/ShabalalaWATP/AllSeeingEye/pull/121) remains
unreleased. Its exact `5cc7dbeb` full CI
[37011600827](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/37011600827)
passed, but PostgreSQL whole-job cost was **45.3833 runner-minutes**, above the
under-30 KAN-71 requirement. Every previously selected case remains in the
2,867-ID census. Five over-target repetitions would not satisfy acceptance and
have not been requested. The next narrowly reviewed schema-inventory candidate
has passed 115 correctness cases. Its fixed four-arm local mechanism comparison
measured a 12.1977-second median saving, with the post-measurement cleanup-verifier
failure and independent absence proof retained explicitly. This is not whole-CI
acceptance. See the [scoped inventory review](../reviews/2026-10-02-KAN-71-schema-inventory.md).

KAN-73 separately retains its controlled 88.0644-second full-suite improvement,
126 Node test files, unchanged branch totals and coverage within 0.05 percentage
points. This meets its measured local criterion, with follow-up delivery still
requiring approval. KAN-70's twenty-run main observation and KAN-75's four weekly
dependency observations remain incomplete. No successful production rollout or
completion of these elapsed requirements is claimed.
