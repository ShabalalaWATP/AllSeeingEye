# SEC source provenance integration gate

Status: implemented in the combined integration checkout, with focused acceptance passed. Required full combined acceptance remains incomplete. Passing checks in either isolated branch do not satisfy this gate. The initial combined baseline reproduced the stale media capture-as-publication assertion (23 passed, one failed); that expectation was corrected and truthful public/private date selection was pinned. The first combined implementation run passed 45 tests, including authenticated SEC import, operator declaration, report generation, reload and ZIP/DOCX export.

## Integration sequence

1. Merge source provenance and SEC filing changes while preserving both sets of behaviour. In `backend/src/ase/api/routers/research_inputs.py`, retain the generic `_complete_connected[T]` needed by SEC alongside the declaration routes and their final session, expiry and owned-input checks. Regenerate API contracts after the combined implementation is stable.
2. Establish exact original-date handling in `adapters/research_records/sec_history.py` and `company.py`. The selected `SecFiling` stores a parsed `date`. Both selected and automatic parsing now use `parse_filing_date` to require exact canonical input before that conversion. Require an exact ASCII `YYYY-MM-DD` provider string, a valid Gregorian date, and equality with its parsed `isoformat()` before accepting a record. Alternatively retain the original string explicitly through selection and extraction. Do not silently normalise non-padded, compact, week-date or whitespace-bearing provider values and call the result raw provenance.
3. In `company.py::SecSubmissionsProvider._parse`, attach a typed `SourceDate` to each recent or archived filing metadata event. Use `resolve_source_date` with field `filingDate`, the exact original string, calendar `gregorian`, role `publication` and basis `source_spec`. Require a resolved day interval, with an exclusive next-day end. `value` and `published_at` remain absent. The filing day describes issuance, not the reporting period or occurrence of the filing's assertions.
4. In `sec_document.py::extract`, attach the same typed source declaration to every selected document chunk. Do not change original bytes, original SHA-256, extracted text, normalised text digest, event identity, content hash or character locators. Keep capture time separate. The shared `records.py::record_event` currently substitutes observation time when `published` is absent: retain the explicit final replacement to `published_at=None`, or introduce a narrowly scoped option that suppresses this fallback. Do not globally change unrelated record providers during integration.
5. Replace temporary attribute-based qualification in `domain/sec_filing_time.py` with the typed filing-day record. Preserve the exact automatic source and record-kind restriction (`research-sec-submissions`, `filing_metadata`), publication basis and supported source declaration. Require one unambiguous resolved Gregorian publication day; conflicting or unsuitable records must not gain recency. Existing `evidence_time.py` returns no exact timestamp for this case. Never return a synthetic UTC midnight as an evidence timestamp or display it as publication.
6. Retain the current documented calendar-label selection policy: compare the reported filing calendar day with request calendar bounds, admit possible partial-day overlap, and exclude a filing on an upper-bound date when that bound is midnight. This is not a claim about the source timezone or an exact instant interval. Maintain the explanation in automatic collection receipts. Do not silently replace this with timezone inference, a generic all-source day matcher or an occurrence-date policy.
7. Update `domain/input_declarations.py::apply_declarations` so source-populated SEC passages can receive their first bounded operator declarations. Preserve existing source-origin transformations and source-specification/source-metadata date rows unchanged. Reject passages with prior operator declarations and reject derivative input chains using the existing parent-input restriction. Assign actor, operator origin and review state on the server; never permit client replacement of source metadata, actor identity, converted values or provenance basis. Enforce at most four total date rows per passage across retained source rows plus new operator rows, and at most four total transformations. Keep the existing eight-passage request cap and private input slot/expiry limits. Refuse an over-budget request rather than truncating metadata.
8. Verify API, readable reports, JSON/evidence ZIP and retained comparison/export digest paths using the existing typed codecs. Update generated contracts and UI labels only where integration actually changes their shape. No migration or rewriting of old evidence is justified merely to add absent provenance fields.

## Chronology and scope boundaries

Automatic filing metadata must qualify through the narrow day policy so the shared collector does not discard date-only records. The policy must retain shared collection budgets, exact selected CIK routing, partial-history notices and honest result counts.

Selected filing content enters the explicit private-input report path. That path currently admits unknown publication instants because the operator supplied the input. Adding source dates must not silently apply the automatic metadata filter to selected passages or imply that selected content occurred within the report window. Show the reported filing day and its uncertainty in the evidence record; preserve existing explicit-input chronology and limitations. Any later change to selected-input filtering requires a separately stated behaviour and acceptance cases.

Generic unknown publication dates, modification dates, unspecified Dublin Core lifecycle dates, occurrence dates and unsupported calendar declarations must retain existing exclusion from public publication-recency selection. A matching attribute name or foreign source ID is not sufficient to acquire SEC filing-day eligibility. Historical frozen evidence remains byte-compatible and is not reinterpreted. No attribute-only runtime fallback is retained. Missing, malformed or conflicting typed records cannot qualify through the SEC shortcut, even when their legacy attributes contain a plausible day. Frozen historical records and their canonical bytes are not rewritten.

## Required acceptance cases

- [x] A real fixture-backed recent filing and an archived filing pass through `ResearchCollector`, retain typed filing-day provenance, keep `published_at=None`, and produce correct retained attempt counts and partial-history explanations without additional provider requests.
- [x] Half-open date cases cover a possible partial-day match, an upper bound exactly at midnight, an out-of-window day, open bounds, and explicitly offset request bounds under the documented calendar-label policy. No test asserts a fabricated source timezone.
- [x] Unrelated source IDs, selected-content record kinds, occurrence/modification/unspecified roles, malformed or conflicting typed dates and generic unknown publication dates cannot use the automatic metadata shortcut. The recorded-time basis remains unchanged.
- [x] Canonical source strings survive unchanged into `raw_text`; invalid dates and noncanonical date spellings are rejected or explicitly retained by the chosen raw-field design, never silently relabelled. Exercise both selected listing and automatic older-page parsing.
- [x] Selected document import passes through the actual authenticated private report route, then reload and export. Every chunk preserves the source date, original SHA-256, extracted digest, text/offsets, source identity and absent exact publication time. No public collection or global event-store insertion occurs.
- [x] A first operator transliteration on a source-dated SEC passage succeeds through the real declaration endpoint and derived receipt. Existing source provenance is identical before and after, the actor is the current user, original text/hash stays fixed, and the original input remains unchanged.
- [x] One retained source date plus three operator date rows succeeds; one plus four fails atomically. Cover the analogous combined transformation cap, prior operator declaration refusal, derivative-chain refusal, stale passage/hash, foreign ownership, revoked session and expired input. Over-budget failures retain neither a partial derivative nor truncated metadata.
- [x] Readable and structured exports expose the typed role, calendar, precision, method, interval, limitations and recorded transformation execution provenance. They do not infer an export-time current model/profile or label the day as an exact timestamp.
- [x] Existing fixed historical content/comparison digest fixtures still match exact baseline values. New day-bearing evidence survives encode/decode, frozen report reload, canonical digest calculation and comparison export, with real `date` values serialised correctly.
- [ ] Combined backend focused tests, static/type/architecture checks and the project's required full acceptance pass after integration. Relevant frontend declaration, selected filing and evidence display tests pass against regenerated contracts. Record exact commands and results when run; leave this gate incomplete until then.

Suggested existing regression homes are `test_sec_filing_time.py`, `test_sec_filing_history.py`, `test_sec_filing_documents.py`, `test_sec_filing_report.py`, `test_input_declarations.py`, `test_input_declaration_sessions.py`, `test_provenance_canonical.py` and `test_query_transliteration.py`. Add a focused integration test module if combining these responsibilities would obscure the behaviour being checked.


## Combined focused acceptance evidence

On branch `codex/source-provenance-sec`, the final focused command passed **164 tests in 69.78 seconds** (session 15686), with coverage disabled to avoid collision with independent acceptance runs:

```text
uv run --project backend pytest backend/tests/test_sec_filing_time.py backend/tests/test_sec_source_declarations.py backend/tests/test_sec_filing_report.py backend/tests/test_sec_filing_api.py backend/tests/test_sec_filing_date_validation.py backend/tests/test_sec_filing_deadline.py backend/tests/test_sec_filing_documents.py backend/tests/test_sec_filing_history.py backend/tests/test_sec_filing_limits.py backend/tests/test_sec_filing_release.py backend/tests/test_media_events.py backend/tests/test_input_declarations.py backend/tests/test_input_declaration_sessions.py backend/tests/test_provenance_canonical.py backend/tests/test_candidate_registry_routing.py backend/tests/test_query_transliteration.py backend/tests/test_research_records_company.py --no-cov -q
```

From `backend`, `uv run ruff check src tests`, `uv run ruff format --check src tests` (1,035 files), `uv run mypy src` (635 source files), `uv run lint-imports` (two contracts kept), `python ../scripts/check_file_length.py` and `git diff --check` passed. No dependencies or migrations were added. The API merge conflict is resolved, retaining generic connected-operation handling and final declaration release guards.

The integration owner regenerated OpenAPI and TypeScript contracts. Final frontend
`pnpm test` passed 1,064 cases across 210 files, with no skips and coverage of
95.12% statements, 90.23% branches, 93.69% functions and 96.49% lines. Final
`pnpm typecheck`, `pnpm lint` and `pnpm build` passed. Independent security review,
configured Bandit and the staged Gitleaks hook passed. Full combined backend
acceptance is running on the frozen backend snapshot; the last checkbox above
remains deliberately incomplete until its terminal result is known.
# Final backend regression follow-up, 8 September 2026

The repaired checkout has subsequently advanced to accepted FIRMS main `cef6f7b`.
Safety stash `55f93e73bcc63880e91f657d2d7da759edec5851` and an ignored binary
patch preserve the prior staged tree `59681c994259e672f02c2af4841346d2513eff83`.
Both development-status conflict sections were retained; runtime merges add only
the expected FIRMS wiring and accepted route-preload fixtures. OpenAPI and frontend
types were regenerated from the combined backend. Ruff and mypy (643 files) pass.
The combined focused suite passed 57 tests. Frontend acceptance passed all 1,088
tests in 213 files: 95.15% statements, 90.30% branches, 93.72% functions and
96.54% lines. Frontend lint, type checking and production build passed. The
new full backend acceptance remains in progress; the earlier full-run result below
does not establish acceptance of this newer runtime.

Full acceptance finished with 3,432 passed, 70 skipped and one failure
(94.93% coverage, 6,390.82 seconds). The failure exposed unexpected HTTP 304
escaping the unconditional SEC client instead of returning a safe failed-source
receipt. The client now converts it to a fixed FeedFetchError without response
details or a retry. All 29 affected transport/document/history cases passed after
the fix, with Ruff and format checks passing. Full acceptance of the repaired
tree remains outstanding. Later Companies House and Find a Tender checkouts
still running their original suites must receive this repair after those runs.

## Final repaired combined acceptance

The repaired SEC/provenance plus FIRMS backend full run completed successfully:
3,470 passed, 84 skipped and 94.94% coverage in 6,346.12 seconds. Original process
87233 exited 0; evidence is `data/sec-firms-backend-full.log`. This supersedes the
pending repaired-run status above. Frontend acceptance remains the passing
1,088-test run with unchanged coverage gates, type checking, lint and build.
Later Companies House, retention, version-monitoring and procurement additions
remain separate integrations. No live SEC contact, operator database or deployment
was changed by these fixture-based checks.

## Main integration

The SEC/provenance milestone was combined with the accepted structured report
export and exact-version release changes. Both document merge points preserve
source-provenance metadata and directional inline text. The resulting main
checkout passed 25 focused export/provenance tests in 74.15 seconds, Ruff and
whole-source mypy (645 files). Its frontend is byte-identical to the accepted
1,088-test SEC/FIRMS frontend snapshot. The feature's repaired full backend run
passed 3,470 tests; no separate full run of this document-only union is claimed.
