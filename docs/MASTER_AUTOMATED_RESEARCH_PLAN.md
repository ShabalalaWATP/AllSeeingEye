# Automated research implementation plan

Status: software implementation committed in `de72899`; combined software checks pass.
Configured-model quality evaluation remains open. Checked items below describe
implemented behaviour within the documented limits, not measured research accuracy.

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
