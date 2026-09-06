# OSINT product direction: automated research for an operator

Updated 6 September 2026 following Alex's explicit change of direction. This
supersedes the earlier proposal centred on cases, assignments and team review.
Phase 5/6 and the previous improvement and evidence-scoring milestones remain
completed history. The broader automated-research milestone is now in progress;
[the current implementation plan](MASTER_AUTOMATED_RESEARCH_PLAN.md) records
partial integrations, verification and all remaining acceptance requirements.

## Product objective

An operator should be able to ask a question, obtain relevant public information
quickly, and receive an analysis or report whose evidence and limitations they can
inspect. The main workflow is:

**Question → bounded collection → evidence assessment → answer/report → follow-up.**

Keep the root 3D globe and the existing working views. Make research accessible
from those views and from a simple question entry point. Teams provide basic
sharing of saved research, reports, watchlists and access, without becoming a
case-management or staff-management product.

The existing report engine, frozen evidence, translation, watchlists, schedules,
search and scoped sharing are useful foundations. The existing live-store Ask the
Eye remains bounded by retained feeds. The new `/research` flow adds explicitly
budgeted private collection from supported feeds/APIs; it is not unrestricted web
search. A
convincing paragraph cannot compensate for information the application never
collected.

## What to learn from public OSINT practice

Bellingcat distinguishes discovery, preservation, verification and analysis.
For this product those are useful stages to automate where feasible, while making
uncompleted checks visible. Its published workflow does not establish that an LLM
can perform every verification step. [Bellingcat workflow](https://yemen.bellingcat.com/methodology/workflow/).

Original context and capture records matter. Saved snippets, source links and
hashes support traceability, but are not preservation or authentication of the
original page, image or video. The product must describe exactly what was saved.
[Berkeley Protocol](https://www.ohchr.org/sites/default/files/2024-01/OHCHR_BerkeleyProtocol.pdf),
[WITNESS evidence guidance](https://archiving.witness.org/archive-guide/resources/video-as-evidence/).

These are design lessons, not a claim of endorsement or evidential accreditation.

## Priority 1: dependable automated answers

The completed evidence-scoring milestone addresses weighting and report transparency.
See [the scoring policy](REPORT_EVIDENCE_SCORING.md) for the exact matrix, examples,
doctrine mapping and limitations. Each judgement receives a frozen engine-authored
assessment separate from the model's proposed likelihood and confidence.

Useful outcomes:

- Strong graded information can carry more weight than many weak reports.
- Copies and shared parent organisations do not become extra corroboration.
- Supporting and opposing evidence remain visible, including weaker opposition.
- Unknown source reliability or information credibility remains unknown.
- Unrelated material elsewhere in the report does not lower a judgement's ceiling.
- Readers see why confidence is constrained and what evidence would improve it.
- Exports carry the same assessment as the saved version, without retrospectively
  applying new policy to old reports.

Report quality should be shown as separate dimensions: evidence support,
unresolved conflict, source coverage, citation validity and remaining uncertainty.
Do not compress them into an invented percentage of accuracy. Historical
calibration would require labelled outcomes and an evaluation design, not an
arithmetic average of source grades.

## Priority 2: research a question on demand

The active implementation adds question-led collection to the existing report
service. Quick/detailed collection, typed receipts, uploads, follow-ups, challenge,
chronology/identity/source context, progress and contextual actions are integrated.
The table remains the acceptance direction; final whole-suite, security and
configured-model quality gates are still open.

| Stage | Intended behaviour | Acceptance criterion |
| --- | --- | --- |
| Ask | Plain question, optional place/time scope, quick or detailed output | The operator can start without knowing PIR/SIR terminology |
| Plan | Derive bounded queries, entities, languages and appropriate source types | Show the interpreted question and let the operator correct scope |
| Collect | Query supported free APIs/feeds on demand with explicit request/time limits | Show sources attempted, returned, empty, unavailable or unsupported |
| Challenge | Search for contrary evidence and alternative explanations | An unsuccessful challenge is recorded as a coverage gap, not confirmation |
| Answer | Concise answer first, citations and uncertainty next | Each factual passage links to a captured excerpt or is labelled an inference |
| Continue | Ask a follow-up, narrow the time window or request a deeper report | Reuse frozen evidence deliberately and record new collection separately |

Start with one topic family already served well by the connectors, then add
adapters. Do not promise equal coverage for every topic on day one. Free API/feed
availability, terms, rate limits and geographic coverage must be checked before
choosing an integration. Keep network access behind the existing SSRF boundary.
No scraping, paid APIs or additional cloud services are implied.
Persist the question, run summary, bounded selected evidence and resulting report.
Unselected live/search material should expire rather than form a growing archive.

## Priority 3: useful research modes

These remain the intended research modes. Implemented bounded capabilities include
news/social feeds, SEC and optional Companies House metadata, current DNS/RDAP,
optional SSLMate unexpired certificate snapshots and isolated supplied-file
extraction. Full ownership/history research, automated authenticity checks and
representative real-model quality are not established by those components.

| Research need | Useful automated output | Key limitation to expose |
| --- | --- | --- |
| Event or breaking story | What happened, chronology, disagreements and changes | Publication time is not necessarily event time |
| Country, region or place | Recent developments with maps and local-language coverage | Missing regions/languages can distort the picture |
| Organisation or company | Public identifiers, filings, ownership claims and dated links | Name matches are candidates until identity is resolved |
| Domain or public website | Public registration/DNS/certificate history and related identifiers | Shared hosting or infrastructure does not establish common ownership |
| Public claim | Claim-specific supporting/contrary excerpts and an uncertainty statement | A citation does not establish that the excerpt entails the claim |
| Document or dataset | Extracted facts, tables, entities and a sourced summary | Extraction errors and dataset scope must survive into the answer |
| Image/video supplied by the operator | Metadata, OCR/transcript and verification leads | Metadata and visual similarity alone do not establish origin or authenticity |
| Aviation, maritime, cyber or hazard | Specialist context using existing boards and sources | Feed gaps and sensor limits must be explained before anomaly judgements |

Prefer reusable analysis steps over dozens of shallow dashboards. Follow-up
questions, comparison of sources, a timeline and a map should operate on the same
research result where appropriate.

## Priority 4: source context and evidence improvement

The registry now records a qualitative inherited-grade basis, scope, limitations,
provenance role and policy version. New selected evidence freezes that metadata;
legacy absence stays unknown. No historical review date or performance estimate
is invented. Richer subject/geographic expertise and independently reviewed rating
history remain future work. Do not infer independence from separate domains alone.

The authenticated source catalogue also covers all supported research editions,
social feeds, public-record adapters and private imports. These research profiles
are explicitly F/unassessed with source-specific limits. Optional account-backed
services remain visible as capabilities when keys are absent, with unavailable
collection receipts. Platform reputation never becomes an unknown publisher's grade.

For an individual claim, distinguish a direct observation or primary record from
an outlet quoting someone else. Recover original attribution through supported
structured data where available. Check whether multiple articles cite the same
wire story or original statement. Keep unresolved attribution explicit.

Frozen citation checks now expose captured excerpts and review cues. Continue to evaluate
whether the cited passage actually supports the sentence. Such checks need
fixtures and measured failure rates, including negation, quotations, dates,
ambiguous identities, translation and missing context. A second model's agreement
is not an independent source.

Source grades and the evidence matrix are revisionable policies. Persist which
policy and metadata a report used. Future corrections should create a new report
version and explain changed evidence, rather than silently rewrite history.

## Existing views and basic sharing

| View | Recommended development |
| --- | --- |
| Globe | Keep default; add an obvious research action for the selected event/place |
| Reports | Become the saved research library with question, scope, answer and evidence |
| Report reader | Lead with findings; reveal scoring, excerpts, timeline and method on demand |
| Direction | Offer simple saved research/watchlist forms while retaining advanced requirements |
| Trackers | Add explanatory coverage/freshness and a relevant question/report shortcut |
| Warning and schedules | Turn a useful saved question into a recurring report or change alert |
| Teams | Basic membership and explicit sharing scope, using existing authorisation |

Cases, assignees, task boards, staff performance, handovers and mandatory reviewer
queues are outside this direction. Existing automated validation statuses remain
quality signals, not evidence of a human approval workflow.

Contextual research actions now connect the globe and specialist views to a scoped
question. Saved questions can drive schedules and deterministic change alerts;
document/media schedules are rejected because private inputs expire. Changes are
not automatically classified as verified corrections. Upload focus remains private
and never sends extracted terms to public search providers. See the
[implementation plan](MASTER_AUTOMATED_RESEARCH_PLAN.md) and
[API contract](api/AUTOMATED_RESEARCH_API.md) for precise limits and remaining gates.

## Measures of usefulness

Evaluate time to a useful sourced answer, citation correctness, whether important
counterevidence was found, coverage honesty, cost/request limits and the operator's
ability to inspect a conclusion. Use a small repeatable set of representative
questions before widening source coverage.

Keep test results separate from real-world model performance. Scripted gateways
verify application behaviour; they do not measure research quality. A configured
model run and human review of the included labelled synthetic evaluation set are
still required for that assessment.
