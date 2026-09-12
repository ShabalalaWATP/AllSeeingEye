# Automated research implementation plan

Status: research workspace implementation committed in `ab6e226`, with country
subject matching in `b9f9050`. The local OpenAI connection is active; successful
long-report completion and wider model-quality evaluation remain open. Checked items below describe
implemented behaviour within the documented limits, not measured research accuracy.

## Cyber threat intelligence, 12 September 2026

- [x] Add a dedicated CTI workspace with 2/5/7/14-day periods, typed source
  reporting, daily volume charts, search and source-supplied country context.
- [x] Connect seven official/vendor publisher feeds to existing collection and
  private research; repair current ransomware fields, IODA bounds and KEV actions.
- [x] Package 176 licensed MITRE Enterprise ATT&CK actor profiles with historical
  dates, technique links and conservative name matching, not automatic attribution.
- [x] Reuse owner/window-scoped daily research for a cited cyber briefing and the
  professional report reader with existing exports.
- [x] Add an off-by-default Cyber shield layer and filters to map/globe, including
  explicitly labelled, opt-in country reference markers and selection clearing.
- [x] Keep aggregation bounded and outside the shared source-control lock; recheck
  source/session access before release and preserve unknown evidence states.
- [ ] Evaluate configured-model cyber briefing quality and factual attribution
  against representative source sets. Wider archives and geographical coverage
  require explicit source evaluation.

See [the cyber workspace guide](CYBER_THREAT_INTELLIGENCE.md) for source checks,
operator controls, performance limits and evidence semantics.

Acceptance: 2,210 frontend tests pass with one skip and 95.25% statement/90.48%
branch coverage. The CTI backend slice passed 67 tests with 99.33% scoped coverage;
actor/feed/shared suites also passed. Static checks, build, fixture-browser views
and anonymous API rejection were verified. One unrelated source-rating baseline
failure remains documented in the development story. Real-model evaluation is
still an open acceptance item.

## Research types, schedules and photo workspace, 12 September 2026

- [x] Offer Basic, Deep and Advanced with distinct collection/evidence limits and
  indicative narrative targets; preserve saved Quick/Detailed wire values.
- [x] Apply the same choices to one-off, drawn/saved-area research, preferences
  and recurring schedules, including regeneration and resumed drafting.
- [x] Give scheduled research a normal report composer and separate timing panel,
  with edit/pause/resume/delete, status filters and latest successful report access.
- [x] Preserve legacy hourly/template-default windows and clear irrelevant hidden
  subject fields when scope changes; serialise local schedule controls.
- [x] Move photo geolocation to its own primary navigation destination with an
  old-route redirect, six-photo preview set and one combined vision analysis.
- [x] Retain per-photo findings, cross-photo contradictions, bounded candidate
  locations and independent verification steps in the derived report evidence.
- [x] Bind every parent photo to current ownership/security generation, consent,
  expiry and deletion. Keep previews transient and original photos out of reports.
- [ ] Evaluate actual Basic/Deep/Advanced lengths and geolocation accuracy against
  known examples using a configured live model. Unit/fixture tests do not establish
  real-world accuracy or guarantee narrative length.

See [the workspace guide](RESEARCH_WORKSPACE_OPERATIONS.md) for operator behaviour
and limits. Acceptance: 209 selected backend tests and 1,993 frontend tests pass
(one frontend skip); statement/branch coverage is 95.09%/90%. Static checks, build
and desktop/mobile fixture-browser checks pass. No schema migration or new runtime
dependency is required.

## Eye assistant, 11 September 2026

The implemented interactive slice is the [floating Eye assistant](EYE_ASSISTANT.md),
separate from long report generation. The existing Max reasoning connection stays
selected; full report acceptance remains open independently of the chat checks.

- [x] Add an accessible draggable Eye launcher across authenticated workspaces.
- [x] Search bounded retained public events, cached camera metadata and packaged
  infrastructure, with explicit scope and coverage limits.
- [x] Validate concise answers and citation membership, preserve the selected
  model, and enforce cancellation, source controls and current access.
- [x] Verify behaviour, browser layout and one real configured-model answer.
  Final content acceptance covered six refetched USGS records. Broader factual
  accuracy and complete provider coverage are not established by this check.

## Source audit and activation, 10 September 2026

The active next milestone is the [research workspace overhaul](RESEARCH_WORKSPACE_OVERHAUL.md):
multiple countries, historical periods, photo geolocation, native web context,
monthly recurring research and clearer navigation. Live configured-AI evaluation
remains open. See [operator flows](RESEARCH_WORKSPACE_OPERATIONS.md).

The current operational findings and ranked onboarding queue are in
[SOURCE_CONNECTION_AUDIT.md](SOURCE_CONNECTION_AUDIT.md). Configuration presence,
current delivery and research capability are separate acceptance criteria.

- [x] Inventory every scheduled source, research capability and camera provider;
  audit server-side key presence without recording values.
- [x] Check all 38 RSS seeds once with bounded requests; record baseline failures
  and successful UN/SCMP repair checks separately.
- [x] Connect the existing 21 official/general publisher feeds to private headline
  research with original source controls and provenance.
- [x] Interleave feed families within existing budgets and preserve existing
  explicit tasks when the expanded catalogue reaches the plan row limit.
- [x] Add fresh USGS/EONET area searches with exact geometry/time filtering,
  source disable inheritance, cancellation and truthful page limits.
- [x] Reject legacy EONET polygon centres from exact retained-area evidence.
- [x] Verify current FIRMS delivery and add AISStream compression diagnostics.
- [x] Restore browser/command access and link the completed OpenAlex account:
  optional server-side key, origin-bound Bearer header and a successful bounded
  live metadata query (11 September UK time).
- [x] Connect WSDOT's official access-code API with protected credentials, existing
  camera cache/limits and live catalogue/sample-image verification: 1,630 active
  snapshot cameras on 11 September, no continuous video supplied by this API.
- [x] Connect the operator's SSLMate CT Search account through the existing
  exact-hostname provider, with a successful seven-record live query on 11 September.
- [x] Create a dedicated BarentsWatch AIS client and verify its token and public
  latest-position endpoint, separate from the operator's general `api` client.
- [x] Add bounded BarentsWatch snapshot polling, cached credentials, shared source
  controls and map attribution; production connector accepted 3,407 fresh positions
  on 11 September. The military label remains an unverified AIS assertion.
- [x] Verify the operator's OpenAQ key and connect bounded area research with
  exact station/measurement geometry, acquisition dates, original units and
  per-dataset reuse/attribution checks. The actual research service accepted six
  dated readings from two London stations on 11 September. Latest values are
  partial coverage, not a historical series or health assessment.
- [ ] Complete remaining free provider account linking. OS email is verified and other prepared
  registrations still require the operator's authentication steps.
- [x] Restore, test and activate the operator's OpenAI Luna profile at maximum
  reasoning through the normal audited application connection use cases.
- [ ] Complete live report acceptance and representative model-quality evaluation.
  Two photo examples passed; long reports and web source quality exposed failures.
  See [live acceptance](LIVE_RESEARCH_ACCEPTANCE_2026_09_11.md).
- [ ] Extend secure administrator credential management beyond FIRMS and AI.
- [ ] Add approved OS/Companies House credentials, ReliefWeb appname/UCDP
  access, authorised camera keys and validated primary dataset imports.
- [ ] Add regional context beside exact-area evidence; integrate fresh FIRMS,
  BarentsWatch historical queries, MET Norway, OpenAQ historical series, humanitarian aggregates and dated imagery
  in the priority order and within the rights recorded in the audit.
- [ ] Measure geographic and temporal delivery, deduplicate original sources,
  and verify each new provider's source-disable and report citation behaviour.

## Acceptance checklist

- [x] Question-led research with quick/detailed collection, explicit date,
  language and topic scope, deadlines, cancellation and bounded request budgets.
- [x] Free news and social adapters, including foreign-language queries and
  original publisher/account attribution without inheriting platform trust.
- [x] Every registered source has a qualitative rating basis and limitations;
  unknown publishers remain explicitly unassessed. Freeze policy with reports.
- [x] Collection receipts distinguish attempted, empty, failed, unavailable and
  unsupported sources, and expose temporal/language coverage and gaps.
- [x] Private research collection integrates with existing scoped report
  generation, without publishing private inputs into the shared live store.
- [x] Passage-level citation checks, counterevidence for every key judgement,
  source chains, event/publication chronology and cautious identity resolution.
- [x] Follow-ups reuse authorised frozen evidence and record new collection.
- [x] Saved-question schedules and meaningful changes/corrections monitoring.
- [x] Company research through supported public records and identifiers.
- [x] Domain research through guarded public registration/DNS/certificate APIs.
- [x] Bounded document/dataset import with page/row citations.
- [x] Supplied image/video metadata, OCR, keyframes and verification leads,
  with safe parsing and explicit unavailable capabilities.
- [x] A focused research interface, contextual research actions in existing
  views, accessible evidence/progress inspectors and simple team sharing.
- [ ] Representative labelled evaluation set and actual configured-model run;
  report research-quality measurements separately from software test results.
- [x] SQLite/PostgreSQL integration, frontend behaviour/browser checks,
  security review, static checks, coverage gates and export consistency.
- [x] Updated architecture, source catalogue, API/operations documentation,
  development story and coherent commits.

## Implementation boundaries

Keep the root globe, Evil Eye branding, existing modular monolith and scoped
access policy. Use free feeds/APIs only, no scraping or new cloud services.
Only selected frozen report evidence and bounded run/configuration metadata are
durable. Unselected collection and uploaded originals expire. Collection occurs
outside database locks, with fresh authorisation before saving or returning work.
Never describe qualitative grades as measured accuracy percentages or model
agreement as independent corroboration.

## Current delivery status, 6 September 2026

Implementation commit `de72899` follows `99c1e16`. No Git remote is configured.
The final verification record below supersedes pending-check notes in the
component delivery log. Configured-model evaluation remains outstanding.

| Slice | Implemented so far | Remaining acceptance |
| --- | --- | --- |
| Question and collection | Quick/detailed private collection, explicit question/languages/window scope, provider receipts, request-bound cancellation and private progress polling | Configured-model evaluation |
| News and social | Google News edition queries and configured public social feeds, captured publisher/account hints, unassessed research grades | Representative coverage evaluation; editions do not prove translated or local-language coverage |
| Source policy | Live and research catalogues include every known provider/private-input ID, source-specific basis, scope, limits and frozen policy; research sources are F/unassessed | Catalogue availability is not operational availability; no measured historical accuracy |
| Evidence inspection | Frozen attributes, citation checks, chronology, identity candidates, source chains, challenge disclosures and shared exports are integrated | Representative model-quality evaluation |
| Private collection | Only selected evidence and bounded receipts are saved; research results use a separate transient store | Resource isolation is not an OS security sandbox |
| Company and domain | SEC, optional authenticated Companies House, current DNS/.com/.net RDAP and optional authenticated SSLMate certificate snapshots | No complete company/ownership register or historical DNS; certificate first page is unexpired issuances, not complete history |
| Scheduled research | `0015` saved questions/options; `0016` opt-in deterministic change summaries and schedule alerts; document/media schedules rejected | Changes are not verified corrections |
| Documents and media | Bounded isolated extraction, expiring private input, preview/report handoff and frozen input metadata without transient IDs; actual Linux runtime checks pass | Unfixed distribution advisories and native decoder isolation remain deployment considerations |
| Research interface | `/research`, `/sources`, uploads, follow-ups, challenge/context inspectors, progress and contextual actions across existing views | Browser checks used synthetic API responses |
| Evaluation and release | Combined software checks and local images pass; implementation committed | Configured-model choice, human-reviewed references and actual quality evaluation remain open |

## Runtime and provider limits

Quick collection admits at most six requests, 45 seconds and 200 retained items;
detailed collection admits 24 requests, 180 seconds and 800 items. Per-request
timeouts are 12 and 20 seconds respectively. Provider calls are admitted serially;
unsupported and exhausted attempts are recorded. These are collection budgets,
not a guarantee about total report latency or upstream completeness.

The additional challenge pass has one shared six-request, 45-second,
200-item budget across judgements. Its producer integration has passed focused tests; final combined checks remain.
An empty or exhausted search must not be presented as confirmation. Document and
media focus must not send extracted private terms to public providers.

Google News RSS is undocumented. The implementation considers at most 200 feed
items, retains dated items in the requested interval and fetches no article HTML.
Configured editions include simplified/traditional Chinese as well as other
languages; supplied phrases are not automatically translated. Edition selection
is neither a language check nor proof of geographic or Chinese-source coverage.
Public social collection uses configured feeds, not unrestricted platform search.
SEC returns bounded metadata, DNS/RDAP return explicitly labelled current snapshots.
Quick domain research requests A records; detailed research requests A, AAAA, MX
and NS, each as one admitted request. Companies House and SSLMate are implemented
optional authenticated providers. Without their operator keys they return unavailable
without a request. See [source contracts](02_DATA_SOURCES.md#q-active-automated-research-integration-6-september-2026).
Free feed/API scope does not imply unrestricted reuse or continuing availability.

One API process owns application admission and transient stores. Killable parser
subprocesses do not create extra API workers or a persistent processing service.
Original uploads are transient and no raw corpus is added. Extracted input access
expires after 15 minutes; physical removal is lazy on the next store access, with
memory caps still enforced. Unselected research material stays transient.
Document extraction accepts at most 8 MiB, 50 PDF pages, 200 passages/rows and
200,000 extracted characters. Locator types remain explicit, including PDF physical
page, CSV row/line range, JSON pointer and DOCX paragraph rather than invented pages.
Media adds bounded derivatives and English OCR, with no authenticity verdict.

A hash-verified FFmpeg 9.0.1 Windows runtime was placed under ignored `data/` for
synthetic checks. It is not a committed application binary. The production API
Dockerfile adds distribution parser/media tools. An initial updated image build
passed; its Trivy scan found zero fixable HIGH/CRITICAL findings but 233 total
unfixed findings (7 CRITICAL, 226 HIGH). These are package-level findings with
duplicates, not 233 validated reachable attack paths. None has yet been validated
as reachable in this application. This is not a clean-security claim.
Both final source images were built and passed the fix-available vulnerability gate.
All 397 checked API source/package files match the final image. No image was deployed.

The worker is a killable resource boundary with fixed arguments and a scrubbed
environment, not an OS filesystem/network security sandbox. A native parser
compromise could retain service-user file access. The container has a read-only
root and no-new-privileges, but its application-data mount remains writable.
Linux `RLIMIT_AS` is 512 MiB per process, not an aggregate process-tree memory cap.

Generation remains synchronous, with a 600-second request deadline and disconnect
cancellation. Optional `X-Research-Run-ID` enables private stage polling with a
30-minute process-local TTL. If saving had begun, a commit can win cancellation;
check Reports before retrying. Follow-ups reuse authorised frozen evidence while
recording new collection separately. The [API contract](api/AUTOMATED_RESEARCH_API.md)
documents input expiry, progress and this saving uncertainty.

## Verification record

Final local verification:

- Full backend: 1,428 passed, two PostgreSQL-only skips, 96.47% branch-inclusive
  coverage. Both skipped cases passed in a separate 19-test PostgreSQL run,
  alongside report/upload session guards. Earlier integration covered 145
  PostgreSQL cases and actual migrations with preserved legacy data.
- Full frontend: 453 tests in 90 files passed; 98.24% lines, 91.32% branches,
  96.12% functions. Full ESLint, TypeScript, production build and narrow/desktop
  browser checks passed. Browser/model fixtures were synthetic.
- Ruff, formatting, strict mypy, architecture boundaries and source length passed.
  Semgrep ran 457 rules on 1,065 targets with zero findings after documenting two
  annotation-import false positives. Gitleaks scanned 5.33 MB of application
  source with no leaks; Python/frontend dependency audits and Bandit passed.
- Both final images built and passed fix-available HIGH/CRITICAL vulnerability
  checks. Actual Linux document, OCR/video, resource-limit, timeout and cancellation
  checks passed. The API image retains the unfixed distribution advisories below.
- [Independent security review](security/AUTOMATED_RESEARCH_REVIEW.md) repaired and
  verified two session-lifetime issues. Review coverage is partial and parser
  resource isolation is not an OS filesystem/network sandbox.

No remote CI, deployment or real-model evaluation is claimed. The following
component results are a historical delivery log, not additional unique test counts.

| Scope | Recorded evidence | Limit |
| --- | --- | --- |
| Source ratings and frozen attributes | 51 focused tests; 100% line/branch coverage across five new policy/codec modules; 65 broader regressions; 24 capture/provenance tests; Ruff and mypy passed | Runs overlap and must not be added into a unique test count |
| Research context and persistence | 34 tests including SQL/API legacy and historical round trips; 100% line/branch coverage across context, codec and DTO; Ruff/mypy passed | Historical context is loaded, never recomputed; producer integration is separate |
| Question UI | 10 focused tests; real-browser checks at 1440, 390 and 320 pixels, error/retry and saved-report navigation | Scripted API responses, not real collection/model quality |
| Receipt/citation/source reader | 41 focused tests in eight files, typecheck/build/scoped ESLint; browser disclosure, citation focus, catalogue search and narrow layouts | Upload/follow-up/context/challenge UI not covered by this slice |
| Document extraction and shared worker | 90 focused tests, 94.92% scoped coverage, Ruff/mypy/Bandit; actual Windows 512 MiB Job rejected a 550 MiB allocation | Windows results are separate from the Linux runtime checks below |
| Media adapters | 56 tests, 97.39% scoped coverage; synthetic English OCR, H.264 MP4 and VP9 WebM runtime checks; event bridge 11 tests/100%; Ruff/mypy/Bandit | Not an authenticity, manipulation or general codec-quality evaluation |
| Upload boundary | 44 tests, 97.24% scoped branch-inclusive coverage; actual 76 KiB TXT through application and isolated worker; Ruff/mypy/Bandit | Includes disconnect cancellation/cleanup, still requires combined report/UI acceptance |
| Challenge/context integration | 22 focused tests, including four SQL/export/actual scripted-production cases | Model challenge generation/review is scripted; no full-suite or real-model result |
| Integrated PostgreSQL and schedules | 145 scoped PostgreSQL tests and actual migration verification passed; 23 schedule regressions include document/media rejection | Disposable databases only; no operator migration or final whole-suite result |
| Source catalogue | 11 source-list/catalogue/frozen-evidence tests; Ruff/mypy/Bandit passed | Package-targeted coverage hit a NumPy import failure; this is not a coverage pass |
| Contextual interface | 35 focused view-action tests and browser checks | These overlap the integrated frontend suite |
| PDF international text | 15 tests, 98.77% scoped coverage; bundled Greek/Cyrillic glyph support and explicit Arabic/CJK fallback | Fallback is not full Arabic shaping or CJK rendering support |
| Full frontend | 453 tests across 90 files passed in 112.25 seconds; 98.24% lines, 91.32% branches, 96.12% functions; production build and types passed | Initial full ESLint failure was fixed and scoped checks passed; full rerun pending |
| Linux initial image | Actual TXT/CSV/PDF/PNG, Tesseract, H.264 MP4 and VP9 WebM passed; worker/Tesseract 512 MiB per-process limit observed, 550 MiB allocation rejected; stopped-worker cancellation/timeout reaped children and removed temporary files | Initial image snapshot; not an aggregate memory or filesystem/network sandbox |
| Long-running session boundaries | 140 focused security tests pass; four independent paused-upload/report logout/expiry checks returned 401 without retaining input or report | Full backend coverage and final integrated security gates still pending |

## Remaining work and release gates

Bedrock follow-up, 6 September 2026: administrators can configure a native Amazon
Bedrock Converse text connection using a region, Bedrock API key and manual model
or inference-profile ID. It follows the existing test and confirmed global/team
assignment flow. All text stages retain the selected provider, and frozen reports
record it. Migration `0018` preserves existing OpenAI assignments and test hashes.
See [connection progress](AI_CONNECTIONS_PLAN.md#native-bedrock-extension) and
[operator instructions](AI_CONNECTIONS_OPERATIONS.md#amazon-bedrock). Scripted
provider tests do not close the live account or research-quality gates.

Administrator workspace follow-up, 6 September 2026: administration now has a
dedicated guarded shell and `/admin` overview, including team management and AI
connections. Only active administrators see its entry; the shell verifies current
authority before mounting pages and periodically while visible. Research stays
separate, with explicit navigation between the two areas. See
[administrator operations](ADMINISTRATION.md) and the
[scoped access review](security/ADMIN_WORKSPACE_REVIEW.md). A validated
post-revocation activation/reset-link response issue was fixed with eight
regressions; this does not change the research-quality release gates below.

Evaluation follow-up, 6 September 2026: the harness now supports explicit synthetic
provider replay through the production collection service, request budgets and
detailed challenge/redraft path. Two separate scenarios cover later correction
evidence and unavailable coverage. Interrupted runs preserve model-call records.
The combined evaluation/collection/production regression selection passed 62 tests;
the 36-test evaluation selection measured 94.06% branch-inclusive harness coverage.
Ruff, formatting, mypy over 374 source files, Bandit and file-length checks passed.
These checks use scripted models and do not close the configured-model or
representative human-labelled research-quality gate. See
[evaluation instructions](../backend/evaluations/README.md).

- The user selected OpenAI `https://api.openai.com/v1`, `gpt-5.6-luna` at Max
  reasoning on 6 September 2026. The administrator connection work is tracked in
  [AI connections](AI_CONNECTIONS_PLAN.md), with [operator instructions](AI_CONNECTIONS_OPERATIONS.md).
  Enter the account key through the app, review the included eight synthetic
  evaluation cases and reference judgements, and run the real pipeline against
  that model. Report quality/citation measures separately from software coverage.
- Configure optional Companies House/SSLMate credentials only when those capabilities
  are required; missing keys remain explicit unavailable receipts.
- Before deployment, triage remaining distribution advisories and assess stronger
  native-decoder isolation. This milestone does not claim production deployment,
  unrestricted source coverage, verified identities or full Unicode PDF support.

## Personal MFA follow-up, 6 September 2026

- [x] Direct AI-assisted OSINT login copy and automatic password-then-MFA flow.
- [x] Personal authenticator/email configuration for every active account.
- [x] Mandatory administrator enrolment and persistent MFA session assurance.
- [x] SMTP delivery, bounded proofs, factor-change revocation and host-only recovery.
- [x] Security review and regression for exception-log local-variable disclosure.
- [ ] Operator migration `0019`, persistent encryption/SMTP configuration and real mail check.
- [ ] Routine pruning of expired MFA challenge rows, which currently remain stored
  but cannot be used after expiry. No cleanup job is installed by this milestone.

The MFA operations guide and authentication API describe the new contract. Full
integration verification for this change is recorded in the development story.


## Personal profile milestone, 6 September 2026

- [x] Four personal settings sections for every role, separate from administration.
- [x] Editable name, timezone/date format and private research/report defaults.
- [x] Defaults consumed by research forms with URL/follow-up precedence; output
  language/style frozen with the report; preferred export stays a presentation choice.
- [x] Device/session inspection and confirmed individual/all-other revocation.
- [x] Single-use recovery codes, fresh proof for rotation and local authenticator QR.
- [x] Security review findings fixed: live-family profile revalidation and aborted
  browser mutations across identity changes.
- [x] Arabic/Chinese PDF limitation disclosed, with DOCX/Markdown alternatives.
- [x] Final combined verification completed; coherent local milestone on `main`.

Email remains read-only; verified email changes, uploads, passkeys, notifications
and personal research libraries are outside this milestone. English judgement
validation remains enforced. See [profile operations](PROFILE_OPERATIONS.md).


Profile verification: 552 frontend tests passed (98.12% lines, 91.83% branches).
The full backend run passed 1,741 tests and skipped 14 environment-dependent cases;
one old report-scope assertion was corrected and all five report-suite cases then
passed. Combined backend coverage is 96.40%. Static checks, production build,
OpenAPI consistency, dependency audits, secret scanning and all pre-commit hooks
pass. No remote push, production migration or live SMTP/model evaluation was performed.


## Next expansion plan, 6 September 2026

[Research expansion implementation plan](RESEARCH_EXPANSION_IMPLEMENTATION_PLAN.md)
is the proposed next backlog following `60f57e4`: deeper Russia, China and Iran
coverage; query planning, claims, entities, history and verification; and shared
improvements to the existing globe and flat map. Its companion
[source matrix](REGIONAL_SOURCE_EXPANSION.md) records access/verification limits;
the [geospatial specification](GEOSPATIAL_RESEARCH_PLAN.md) defines geometry,
precision, private overlays, projection parity and acceptance tests.

These documents are plans, not implemented connectors, activated sources or
measured research-quality claims. Existing completed milestones remain above.

## Main-map area research, 10 September 2026

Direct area research now starts from the right-hand map toolbar without an
existing report. The operator draws a boundary, optionally asks a question,
checks source capabilities and confirms collection. The existing private report
pipeline preserves exact geometry, hash, interval, source receipts and citations.
An area-only retained-public-feed provider complements supported external
queries, with bounded fair sampling, original source controls and explicit
coverage gaps. See [area research](AREA_RESEARCH.md) for implemented capabilities
and validation limits. This does not make every catalogue entry spatially
searchable, add a complete historical archive or establish real-model quality.

## Section-based durable research, 11 September 2026

- [x] Persist authorised jobs, frozen evidence and validated topic sections.
- [x] Separate synthesis from topic writing, preserve citation identities and bound splitting.
- [x] Reserve per-call usage before transport and retain uncertain reservations on interruption.
- [x] Fence pause/resume, restart recovery and atomic report publication with database leases.
- [x] Add research-job progress, saved drafts, model/usage details and confirmed discard.
- [x] Complete configured Luna Max reliability acceptance and record actual quality/coverage limits.

The live job completed after an explicit resume, reusing four topic checkpoints
unchanged. The two final steps succeeded; this establishes checkpoint recovery
and bounded publication, not analytical completeness. The optional claim call
reached its existing deadline and retained an unknown-usage reservation.

Next report-quality work identified by this acceptance:

- [x] Add an explicit requirement-completeness check and Needs review outcome for
  unaddressed EEIs, with neutral "not separately assessed" notices.
- [x] Stop final context from copying existing gaps. Improve new-job topic matching
  so common country terms cannot assign unrelated evidence to the first EEI.
- [ ] Collect richer original source material across providers.
- [x] Keep generated web context separate until original-source retrieval and
  provenance checks support its use as retained evidence.
- [ ] Align optional claim-extraction admission/deadlines with Max reasoning and
  report its incomplete outcome without repeating completed report sections.

See [durable research operations](DURABLE_RESEARCH_JOBS.md). Existing direct report
generation and recurring schedules keep their earlier pipeline in this milestone.

## Professional report product plan, 12 September 2026

[Professional report product plan](PROFESSIONAL_REPORT_PRODUCT_PLAN.md) records
one coherent reader document with in-text citations and a numbered reference
list, shared by the browser and Word, PDF and Markdown exports. Supporting
evidence and operational diagnostics now sit outside the default report. The
implemented boundary also covers bounded editorial assembly, requirement
completeness, native tables, safe figures, immutable versions and export
authorisation.

- [x] Shared reader product, reference registry and consistent text exports.
- [x] Editorial quality, retained-original-source boundaries and completeness gates.
- [x] Native chronology tables and safe semantic figure rendering in the browser,
  Word and PDF.
- [x] PDF page inspection, automated compatibility checks and security review.
- [ ] Deterministic source-backed figure/area-map generation and an offline
  Markdown figure bundle.
- [ ] Complete browser and Word visual acceptance, plus multilingual export checks.

The stable affected backend set is clean: a report-focused run passed 1,015 of
1,017 tests before two final compatibility fixes, then the two regressions and
publication coverage passed 9 of 9. The full 5,920-test backend suite was not run.
Backend Ruff, type checking, import contracts and file-length checks passed.
After final combined review fixes for contrary evidence, legacy resume and
reference parity, the focused 39-test report set also passed.

The full frontend suite passed 1,968 tests with one skip and measured 95.1%
statements, 90.07% branches, 93.28% functions and 96.32% lines. TypeScript,
ESLint, the production build and Prettier checks on all changed frontend files
passed. PDF output passed visual page inspection. DOCX structural tests passed,
but visual DOCX inspection remains open because the bundled LibreOffice runtime
is unavailable. Final security review found no actionable findings.


## Subscriptions and daily monitoring, 12 September 2026

- [x] Clarify Research tabs: New research, Saved reports, Plans & areas, with a separate Research progress link.
- [x] Introduce primary-navigation OSINT Subscriptions and preserve old recurring links.
- [x] Add daily, weekly, monthly, three-monthly, six-monthly and annual topic updates, with calendar anchors and editable lookbacks.
- [x] Reuse source choices, countries, conflicts, hazards and authorised saved areas, with explicit boundary disclosure.
- [x] Prioritise new captured content using bounded per-subscription history; preserve context and no-material-update guidance.
- [x] Add a cited Basic Live Monitor briefing reused for 24 hours, protected against duplicate tab admission and premature progress deletion.
- [x] Link reusable research areas to the globe/map and save map drawings as labelled enclosing rectangles.
- [x] Review access changes, date-line geometry, scope preservation and admission consent with focused regressions.

See [research workspace operations](RESEARCH_WORKSPACE_OPERATIONS.md). Live Monitor
refreshes on an eligible visible visit; subscriptions run unattended while the
server is running. Delivery is in-app. Novelty comparison retains 500 content
fingerprints, so it is not a complete semantic archive. Real-model briefing quality,
source archive availability and long-running operator acceptance remain evaluation
work, not outcomes established by fixture tests.

## Economy and personal navigation, 12 September 2026

- [x] Reduce primary navigation to Map, Research, Subscriptions, Geolocation and Economy.
- [x] Keep saved reports, daily monitoring and map-linked areas within Research.
- [x] Add separate profile/settings controls; place team sharing under profile and the source catalogue and alert rules in settings.
- [x] Save per-user Obsidian, Slate and Daylight themes, reduced motion and existing research/report/regional defaults.
- [x] Add global economic headlines and UK, USA, Russia, China and Iran focus controls.
- [x] Connect bounded World Bank annual indicators and ECB daily reference rates, with native histories and exact data tables.
- [x] Add an opt-in, isolated TradingView chart with verified instruments, timing labels and explicit unsupported-market states.
- [x] Add nine public economic feeds, retaining conservative grading, publisher independence and issuer/state-affiliated labels.
- [x] Produce a personal cited Deep economic briefing reused for 24 hours, with historical macro context and normal professional exports.
- [x] Verify source-disable races, observation dates, account isolation, hidden-tab behaviour and existing briefing compatibility.

See [Economy and personal workspace](ECONOMY_WORKSPACE.md) for sources, coverage,
privacy and operating behaviour. Real source probes succeeded; direct local stock
quotes for Russia and Iran remain unavailable in the selected widget. Daily
analysis refreshes on a visible eligible visit. Unattended schedules use
Subscriptions. No real-model quality evaluation or deployment is claimed.

## Deeper economic analysis, 12 September 2026

- [x] Load the market chart automatically, retaining pause/resume and hidden-tab suspension.
- [x] Expand country profiles from four to twelve official indicators, with every miniature history visible by default.
- [x] Add source-linked calculated insights, precise annual changes and explicit observation/coverage gaps.
- [x] Compare countries using the same indicator, units and year, with selectable years and source tables.
- [x] Derive currency pairs from matching ECB dates, showing period movement and observed daily ranges.
- [x] Expand the cited daily assessment and watch conditions, retaining the existing 24-hour job lifecycle.
- [x] Preserve all twelve measures in bounded frozen evidence and the model's source context.
- [x] Verify numerical edge cases, access/data limits, desktop/mobile rendering and automatic chart loading.

The expanded live World Bank probe returned 864 rows within the unchanged HTTP
limit. Backend regressions passed 68 tests; the frontend suite passed 2,098 tests
with one skip and unchanged coverage gates. Documentation and existing market
coverage caveats are maintained in [Economy workspace](ECONOMY_WORKSPACE.md).

## Explicit economic reporting periods, 12 September 2026

- [x] Offer 2, 5, 7 and 14-day summaries, with matching news windows and exact reporting dates.
- [x] Keep the 24-hour refresh cycle separate from the reporting window, with personal per-period job reuse.
- [x] Hide prior-window content immediately and reject mismatched response dates or durations.
- [x] Add a short cited overview above six worldwide headlines and above country reporting.
- [x] Present executive prose, clear assessment sections, retained references and conditions to watch.
- [x] Introduce source-linked country overviews, with annual observation years and unavailable-data handling.
- [x] Extend bounded economic cache retention to 14 days without changing its item or global memory caps.
- [x] Verify period isolation, frozen dates, source filtering, late responses and shared briefing compatibility.

See [Economy workspace](ECONOMY_WORKSPACE.md). Publisher archives and retained
feeds may cover less than the selected interval. Model quality across the four
periods still needs live operator evaluation; fixture tests do not establish it.
