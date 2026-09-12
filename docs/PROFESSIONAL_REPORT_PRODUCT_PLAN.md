# Professional research report product

Status: production-quality milestone implemented and locally verified,
12 September 2026. Timeline and geographic visual generation, and the remaining
cross-format visual and language acceptance, are tracked below. No production
deployment is authorised or claimed.

## Outcome

A completed research task should open one coherent, readable report. The same
saved report should export to Word, PDF and Markdown with matching content,
citations, references, tables and figures. Users should not have to assemble the
answer from separate topic outputs, web context, assessment cards or audit panels.

The default report must answer the research question directly, explain the
evidence and uncertainty, and be suitable for sharing. Generation machinery stays
outside the report. Important limitations remain visible in ordinary language.

## Implemented product

- The backend projects each exact saved report version into one bounded,
  versioned publication made from semantic text, lists, tables, safe local
  figures, citation runs and numbered reference entries.
- The browser, Word, PDF and Markdown paths consume that canonical publication.
  Exports do not call a model, rerun collection or silently include newer data.
- The report opens as a calm editorial reading surface with a concise Export
  menu. Sources, assessment, collection, evidence-map and review tooling are in
  a lazy supporting-workspace drawer rather than the default report.
- Citations use stable first-use numbering and link to one reference list.
  References come from retained evidence metadata and preserve both the public
  source and archived-copy links when available.
- Provider, model, reasoning, prompt, token, attempt and audit detail stays out
  of the reader product and its exports. Review state, evidence gaps and useful
  limitations remain visible in plain language.
- Topic planning now records per-requirement evidence bindings. Generic terms
  no longer assign unrelated evidence to the first requirement, duplicate gaps
  retain their more complete wording, and unsupported requirements produce a
  neutral disclosure and Needs review outcome.
- Word has editable native tables, repeating table headers, bookmarks, linked
  references and bounded PNG/JPEG figures. PDF has searchable text, bookmarks,
  linked references, repeating table headers and bounded figures. Markdown has
  semantic tables and linked references; reports with figures download as a
  portable ZIP with fixed local asset paths.
- Reports with a meaningful multi-judgement citation graph include a deterministic
  evidence relationship diagram. It shows supporting and contradictory links,
  preserves reference numbering and is omitted when it would add no useful
  analytical information.
- Figure decoding and re-encoding, aggregate byte and pixel limits, escaped HTML,
  restrictive renderer policy and late export authorisation protect the expanded
  document boundary. The final security review found no actionable findings.

## The reader's report

Use a restrained document layout with a light reading surface inside the app's
existing dark shell, clear typography, comfortable line lengths and a small brand
mark. Provide a quiet title toolbar with Export, report version/date and access
to supporting evidence. Long reports may have a collapsible contents list.

Suggested structure, adapted to the question and available evidence:

1. **Title and scope:** question, area or subjects, reporting period and evidence
   cut-off. Avoid a full cover page for a short brief.
2. **Executive summary:** direct answer and the most important findings. The
   summary's factual claims also carry citations.
3. **Findings and analysis:** coherent thematic sections combining the retained
   research into a narrative. Distinguish reported facts, attributed claims and
   analytical judgements through clear wording.
4. **Supporting tables or figures:** positioned beside the discussion they help
   explain, only where the evidence warrants them.
5. **Implications and outlook:** include recommendations or indicators only when
   relevant to the user's question.
6. **Limitations and confidence:** concise explanation of evidence strength,
   contradictory reporting, missing answers and important coverage gaps.
7. **References:** one numbered list for all sources cited in the report.

Omit empty sections and unnecessary repetition. Let length follow the task;
do not pad a short answer to fit a fixed page count. Use plain-language headings
rather than internal PIR/SIR/EEI identifiers and validator vocabulary.

## What stays outside the default report

| Reader-facing content | Optional supporting view | Operational diagnostics |
| --- | --- | --- |
| Findings, citations, references and relevant visuals | Retained evidence, original excerpts and source checks | Provider, model and reasoning settings |
| Meaningful uncertainty and unaddressed questions | Claim annotations, alternative reviews and collection coverage | Token usage, attempts, latency and raw rule findings |
| Scope, period, cut-off and publication/review state | Detailed methodology, version comparison and evidence package | Task IDs, prompts, scope JSON, hashes and transport details |

Supporting views retain their existing authorisation. Administration remains
separate. Do not expose administrative diagnostics through a generic evidence
drawer. Keep user-relevant usage/budget information in the research-job view.

The default page should mount heavy evidence maps and review tools only when
opened. Export the reader document by default; offer the evidence package as a
separate explicit action. Do not include model/thinking details in exported
body text, footers, comments or document properties.

Use an honest publication/review state. Successful automated checks do not mean
independent factual verification. If the evidence cannot answer the question,
say so prominently and precisely. Do not turn missing evidence into an assertion
that an event did not occur.

## One saved document and one reference registry

Extend the existing document boundary with a bounded, versioned publication
representation: sections, paragraphs, lists, citation runs, tables, figures,
captions and reference entries. Keep the frozen analytical and audit records.
Expose the reader representation through the existing application/API layers;
generate frontend DTOs from OpenAPI.

The browser and all exports must consume this representation for the exact
selected report version. Exporting must not call an LLM, rerun collection or
silently incorporate newer live data.

- Keep internal evidence identities stable. Assign reader-facing numbers such
  as `[1]` and `[2, 3]` deterministically in first-citation order across the whole
  document, including its summary, tables and figures.
- Put citations beside the claims they support. Avoid a single citation after
  a long paragraph containing several unrelated claims.
- Generate references from retained source metadata, not model-invented titles,
  dates, authors or URLs. Include publisher/author where known, title, date,
  safe source link and relevant access time or page/record locator.
- Reuse the same reference for repeated citations to the same retained source.
  Different articles from one publisher remain distinct references. Do not
  deduplicate solely by domain or merge meaningful source revisions.
- List cited material in References. Keep additional consulted sources and
  research leads in the supporting view.
- Provide citation navigation in the browser, links/bookmarks in documents and
  stable reference anchors in Markdown, with accessible link text.

Retrieve and retain eligible underlying sources before relying on fresh web
research for factual claims. Generated search synthesis is not independent
evidence. If original retrieval is unavailable, retain it as a clearly labelled
research lead and describe any material limitation in the report.

Validate missing/orphan references, claim support, dates, attribution and visual
citations. Existing checks mainly compare key judgements with titles/snippets;
they do not establish support for every sentence. Source count is not a truth
score: distinguish independent corroboration from copied or syndicated stories,
and preserve contrary evidence and source-quality context.

## Coherent writing without another oversized model call

Preserve the durable, checkpointed section pipeline and its usage reservations.
Use a shared outline and bounded editorial work within that pipeline:

1. Map each research requirement to relevant retained evidence. Fix matching
   that lets generic country terms assign unrelated evidence to the first item.
2. Write thematic sections with explicit claim-to-source links and consistent
   entity names, dates and terminology.
3. Produce the executive summary from those saved findings, keeping its source
   links. Check for repetition, inconsistent conclusions and truncated prose.
4. Validate requirement coverage and citations before publication. An unanswered
   requirement must be disclosed as not assessed or unsupported and routed to
   Needs review where appropriate.

Bound any editorial model calls by section and checkpoint their outputs. Retry
only the affected stage; retain cancellation, accounting and current access
checks. Do not repeat completed research or introduce one giant final rewrite.
Changes to planning/checkpoint semantics need explicit version compatibility.

## Tables and diagrams

Start with useful, supportable types: event chronologies, comparison tables,
timelines, reported relationships, and an area map where geography matters.

- Model proposals identify a supported visual type and source-backed data; the
  server validates and renders it. Never execute model-generated drawing code,
  HTML, SVG or Mermaid.
- Give tables column headings, units, time basis and row/cell citations where
  needed. Unknown values remain unknown rather than becoming zero.
- Give figures a number, meaningful caption, legend, source references and text
  alternative. Distinguish reported links from analytical inference.
- Avoid diagrams implying causation, precise locations or certainty absent from
  the evidence. Omit a visual that adds no useful information.
- Freeze figure data and generated local assets against the report version.
  A map figure uses the report's retained geometry/data and proper attribution;
  it is not a screenshot of an unrelated current live map.
- Bound table sizes, image dimensions and asset bytes. Generate assets locally
  from supported data; do not fetch arbitrary remote images during export.

## Export behaviour and formatting

One top-level **Export** menu offers **Word (.docx)**, **PDF** and **Markdown**.
Show progress and actionable errors without exposing internal traces. The
displayed version is the downloaded version.

| Format | Required result |
| --- | --- |
| Word | Editable text, semantic heading styles, native tables with repeating headers, embedded figures, captions, linked citations/references and page-number footer. |
| PDF | Searchable text, A4 pagination, bookmarks/reference navigation, readable typography, table headers repeated over pages, and figures/captions kept together where possible. |
| Markdown | Clean headings, lists, standard tables and linked numbered references. A report with figures offers a clearly labelled ZIP containing `report.md` and local `figures/` assets with working relative links. |

Keep facts, section order, reference numbering and figure content identical.
Use format-appropriate layout rather than promising pixel-identical Word/PDF
pages. Avoid clipped tables, stranded headings, excessive whitespace, decorative
cover pages and citations that become unreadable when printed.

Retain the current local ReportLab and python-docx path for the initial work.
Arabic/Persian shaping is an existing PDF limitation: the optional isolated Linux
browser renderer is not configured by default, and the Windows browser proof
was diagnostic. Multilingual export acceptance must establish supported rendering
and text extraction honestly. Do not declare this solved by changing a font.
Word visual acceptance also needs an available, verified office renderer.

## Delivery order

### 1. Shared reader product and references

- [x] Define the typed publication representation and safe deterministic reference
  registry, extending the existing document boundary.
- [x] Build a clean projection for existing saved reports without new model calls.
- [x] Replace normal browser and all three export inputs with that projection.
- [x] Add the clear Export menu and separate supporting/operational views.

Acceptance: one existing report has the same readable text and citation numbers
on screen and in all downloads; no model/thinking or audit dump appears there.
Material review and coverage limitations remain visible.

### 2. Editorial quality and completeness

- [x] Repair topic assignment, duplicate gaps and requirement-completeness checks.
- [x] Add bounded coherent publication assembly for new durable research jobs.
- [x] Integrate retained original web sources where eligible, with honest treatment
  of sources that cannot be retrieved.
- [x] Apply the canonical publication at the saved-version reader and export
  boundary, including legacy versions, while preserving durable resume
  compatibility.

Acceptance: the known headline-only report fixture cannot silently pass as a
complete answer; missing requirements and contrary evidence remain clear.
Interrupted editorial work resumes without redoing completed topic sections.

### 3. Evidence-driven tables and figures

- [x] Add native, cited chronology tables to the canonical publication.
- [x] Define and validate bounded source-linked figure data, and render tables and
  figures in the browser, Word and PDF with captions and text alternatives.
- [x] Add deterministic source-backed relationship figures when the retained
  citation graph is sufficiently informative.
- [ ] Add deterministic timeline figures and frozen area maps when retained
  temporal or geographic evidence justifies them.
- [x] Package frozen figure assets with Markdown and use working relative links.

Acceptance: every visual has traceable data and citations; tables are editable
in Word, paginate correctly in PDF and remain useful in Markdown.

### 4. Release-quality verification and rollout

- [ ] Complete actual browser, Word and PDF inspection using short and long reports,
  long URLs, many references, conflicting sources, multi-page tables and figures.
- [ ] Verify the intended language set, narrow screens, keyboard navigation and
  print legibility. Document unsupported rendering explicitly until fixed.
- [x] Check content/citation parity, legacy compatibility, safe assets and late
  access revocation before treating the new product as ready.
- [x] Update report API, master plan and development records with actual
  test evidence. Keep each delivery milestone small and independently reviewable.

PDF export has been inspected and is clean. DOCX structure and document contracts
pass automated tests, but a visual DOCX render could not run because the bundled
LibreOffice runtime is unavailable. Browser behaviour has automated coverage;
the broader visual matrix and multilingual export acceptance remain open.

## Compatibility, safety and acceptance gates

Saved report versions and evidence remain immutable. Use a versioned deterministic
projection for legacy reports and store/freeze new publication content for new
versions. Do not rewrite historical analysis or regenerate it automatically.

Preserve escaping, resource limits, render concurrency and the exact-version
authorisation check after rendering. Apply the same release policy to Markdown
and any figure bundle/asset route. Cache keys and asset access must respect the
saved version and current user/team visibility.

Current document tests deliberately reject external relationships, images and
PDF annotations. Update this contract narrowly for safe stored HTTP(S) reference
links and locally generated figures. Keep arbitrary remote resources, scripts,
active content, embedded objects and macros prohibited. Avoid holding the shared
administration lock during rendering or model work.

Required regression evidence:

- Matching body text, citations, references and visuals across all four views.
- No fabricated bibliography entries, broken citation anchors or uncited
  analytical claims silently presented as established facts.
- No provider/model/reasoning/audit metadata in the reader export or properties.
- Correct missing-date, missing-value, unsupported-source and Needs review states.
- Native Word tables and correctly paginated PDF tables, plus an offline-readable
  Markdown asset bundle when figures are present.
- Actual page inspection, including glyphs, bidirectional text and long content;
  automated text extraction alone is insufficient.
- Historical versions remain stable; export performs no new research/model call.
- Revoked sessions/membership, hostile source text, invalid URLs, oversized
  visuals and cancelled render requests cannot bypass existing protections.

## Verification record

- The stable affected backend set is clean. The broad report-focused run passed
  1,015 of 1,017 tests before two final compatibility fixes; those two regressions
  and publication coverage then passed 9 of 9. This is not a claim that the full
  5,920-test backend suite ran.
- A final combined review found three projection and compatibility gaps. After
  preserving contrary evidence and warning fields, legacy directional resume
  inference, and full reference-link parity, the focused 39-test set passed.
- Ruff, backend type checking, import contracts and file-length checks passed.
- The full frontend suite passed 1,968 tests with one skip: 95.1% statements,
  90.07% branches, 93.28% functions and 96.32% lines. TypeScript, ESLint and the
  production build passed, and all changed frontend files pass Prettier.
- PDF output was rendered to pages and visually inspected without clipping,
  overlap or broken tables. DOCX structural tests passed; visual DOCX inspection
  remains open because the bundled LibreOffice runtime is unavailable.
- Final security review found no actionable findings. The review covered safe
  figure handling, output escaping, reference links and late export authorisation.
- The final visual enhancement passed its focused backend and frontend tests.
  A representative relationship diagram and its two-page PDF were rendered and
  visually inspected; the deterministic Markdown ZIP was inspected for fixed,
  working local asset paths and citation parity.
- The final report-focused backend regression passed all 1,035 tests. The clean
  full frontend run passed 1,970 tests with one skip, measuring 95.11% statements,
  90.06% branches, 93.28% functions and 96.32% lines. A competing-load globe
  test timeout passed alone and on that clean full run.
- Heavy figure projection and export preparation run off the API event loop with
  bounded admission and cancellation settlement. Internal generation and archive
  projection wait for capacity; interactive reads and exports fail fast. Final
  correctness and security rechecks found no actionable findings.
