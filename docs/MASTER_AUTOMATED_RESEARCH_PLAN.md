# Automated research implementation plan

Status: research workspace implementation committed in `ab6e226`, with country
subject matching in `b9f9050`. The local OpenAI connection is active; successful
long-report completion and wider model-quality evaluation remain open. Checked items below describe
implemented behaviour within the documented limits, not measured research accuracy.

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
