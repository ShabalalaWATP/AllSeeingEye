# OSINT product direction: automated research for an operator

Updated 6 September 2026 following Alex's explicit change of direction. This
supersedes the earlier proposal centred on cases, assignments and team review.
Phase 5/6 and the previous improvement milestone remain completed history.

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
search and scoped sharing are useful foundations. Ask the Eye currently selects
from the bounded live feed store; it is not a general web research engine. A
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

This implementation milestone addresses evidence weighting and report transparency.
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

Next implementation should make one useful research run work end to end, using
the existing report service and source adapters.

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

These are proposed capabilities, not implemented connectors or verified data access.

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

The source registry currently holds editorial reliability metadata. A future
source profile should record the assessment basis, relevant subject and geographic
expertise, how information was obtained, whether it is a primary or secondary
source, parent organisation and last review date. Do not infer independence from
separate domains alone.

For an individual claim, distinguish a direct observation or primary record from
an outlet quoting someone else. Recover original attribution through supported
structured data where available. Check whether multiple articles cite the same
wire story or original statement. Keep unresolved attribution explicit.

Record passage-level support when APIs supply usable excerpts, and evaluate
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

## Measures of usefulness

Evaluate time to a useful sourced answer, citation correctness, whether important
counterevidence was found, coverage honesty, cost/request limits and the operator's
ability to inspect a conclusion. Use a small repeatable set of representative
questions before widening source coverage.

Keep test results separate from real-world model performance. Scripted gateways
verify application behaviour; they do not measure research quality. A configured
model and a labelled evaluation set are still required for that assessment.
