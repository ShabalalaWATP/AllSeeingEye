# Source language and date provenance

Implementation contract, 8 September 2026. Work has started on
`codex/source-language-date-provenance`, based on integrated main `0c91741`.
Implementation and acceptance remain unfinished.
It addresses the research expansion requirement to preserve original script,
original dates, transliteration and translation separately, and to convert dates
only with an explicit source-calendar contract. It does not establish provider,
conversion-library or semantic acceptance.

## Existing boundaries and verified gaps

- `backend/src/ase/domain/languages.py::matching_text` creates matching keys,
  including explicitly Persian kaf/yeh equivalence. Original evidence and
  zero-width characters must remain unchanged.
- `domain/research_plan.py::QueryVariant` currently records language and terms,
  without distinguishing transliteration from translation or linking each
  transformation to its original term.
- `application/research/query_translation.py` and
  `application/reports/query_preparation.py` record machine query translation.
  Their provenance rules need explicit transliteration handling.
- `domain/events.py` and `domain/evidence.py::EvidenceItem` retain original title,
  English title, language and timestamps, but lack typed source-calendar and raw
  source-date provenance.
- `adapters/feeds/rss.py` parses feed dates and substitutes retrieval time when
  parsing fails. This must not become a claim that publication occurred at capture.
- `domain/evidence_time.py` distinguishes unknown publication dates from retrieval
  timestamps. Preserve that boundary when introducing calendar conversion and
  date precision.

Paths above are relative to `backend/src/ase` unless written in full. Inspect
current code before implementation, particularly legacy feed ordering and expiry
paths that may rely on the existing publication-time fallback.

## Required typed records

Introduce small immutable domain records, in modules such as
`domain/text_transformations.py` and `domain/source_dates.py`.

A text transformation retains:

- Original field or exact original-term reference, original text and source
  language/script.
- Transformed text, target language/script and kind: translation or transliteration.
- Provenance: source-declared, operator-supplied or machine-generated; named
  method/version and actor or model details where applicable.
- Review status and limitations. Transformation does not establish semantic
  equivalence, correct pronunciation or entity identity.

Matching normalisation remains an internal matching operation. Its output must
not replace original text or be represented as transliteration.

A source date retains:

- Exact raw source text and source-field locator.
- Date role, distinguishing publication, occurrence and record validity.
- Declared calendar and declaration basis: source specification, explicit source
  metadata or operator declaration.
- Precision and timezone/offset only where known.
- Status: resolved, ambiguous, unsupported or invalid.
- Converted value or uncertainty interval only where justified, with conversion
  method/version and limitations.

Do not infer a calendar from language, country, digit shape or apparent year.
Do not infer timezone or day/month ordering. Source declaration and operator
declaration remain separately attributed assertions.

## Executable delivery

1. Carry optional typed provenance through `Event`, `EvidenceItem.from_event`,
   `domain/report_records.py`, API evidence schemas and evidence-package manifests.
   Historical records without these fields must remain readable. Omit absent
   additions during historical canonical serialisation so retained digests do not
   change merely because the application was upgraded. Test exact legacy bytes
   and digests, including saved maps and annotation anchors that depend on evidence.
2. Retain raw date text and its field before parsing in `adapters/feeds/rss.py`
   and `adapters/research/feed.py`, including regional feed collection through
   `adapters/research/regional.py`. RFC/ISO feed specifications may establish a
   Gregorian input contract. Invalid or ambiguous input remains unresolved;
   retrieval time stays available separately for capture and operational expiry.
3. Implement actual declared-calendar conversion, not only metadata labels.
   Include Gregorian and a precisely named Solar Hijri convention with explicit
   supported bounds. Review the chosen algorithm or dependency before adoption,
   pin its version where applicable, and verify independently sourced fixtures.
   An unspecified Islamic calendar is insufficient to identify a conversion
   convention and must remain unsupported. Do not claim universal calendar support.
4. Preserve date-only values as dates or uncertainty intervals. Do not manufacture
   midnight UTC or an occurrence instant. Extend `domain/evidence_time.py` filtering
   only through a documented interval contract, with tested ordering and map
   behaviour. Conversion does not increase the original precision.
5. Extend query variants with transformation kind and original-term linkage.
   Provide an operator-supplied transliteration workflow that actually sends the
   intended terms to compatible selected adapters. Preserve shared request,
   deadline and item budgets. A transliteration must not overwrite the original
   query, a supplied translation or an exact registry identifier. Unsupported
   source/script routing is explicit.
6. Preserve transformations through API input, report request scope,
   regeneration, deterministic preview, runtime task receipts and exports.
   Update `query_preparation.py` so transliterations do not acquire incorrect
   machine-translation or replan labels.
7. Provide a bounded declaration path for supplied research records where an
   operator supplies transliteration or declares a source calendar. Freeze the
   declaration in the resulting report, retaining original extracted text.
   Corrections must not mutate earlier frozen evidence. Reuse existing scoped
   input and report boundaries; do not add a disconnected metadata demo.

Operator-supplied transliteration is the proposed executable workflow for this
delivery. Do not advertise an automatic transliteration engine unless it is
implemented and evaluated. Likewise, a source-calendar field without working
declared-calendar conversion does not complete the conversion requirement.

## Interface and exports

In `frontend/src/features/reports/EvidenceAnnex.tsx`, distinguish original text,
translation and transliteration, with method, origin and review state. Show raw
date, declared calendar, conversion status and result alongside the separate
capture timestamp. Ambiguous and unsupported values remain visible.

The research plan editor should let the operator identify a variant as translation
or transliteration, link its original term and inspect the exact outbound terms.
Preview and execution must use the same contract. Preserve labels and provenance
in frozen collection receipts and exported packages, not only the live editor.

## Acceptance requirements

- Persian/Arabic matching equivalence changes matching keys only. Original text,
  zero-width characters, citation text and offsets remain unchanged.
- Translation and transliteration of one original coexist and remain distinct
  through API, saved scope, execution, frozen report and export.
- Fixture providers receive the intended transliterated terms. Unsupported
  variants make no hidden request or silent fallback.
- Identical Latin transliterations do not merge distinct entities. Negation,
  quoted text and exact registry identifiers survive query transformations.
- Gregorian and the explicitly supported Solar Hijri convention have independent
  expected fixtures covering year boundaries, leap rules, supported limits and
  conversion round trips. Tests must not merely compare the converter with itself.
- Persian/Arabic digits retain their original representation even where a parsing
  view normalises digits. Ambiguous numeric dates, unknown calendars/timezones,
  unsupported Islamic conventions and invalid dates remain unresolved.
- Failed feed-date parsing never substitutes capture time as publication time.
  Feed ordering, expiry and unknown-date filtering remain bounded and truthful.
- Date-only/interval filtering, chronology and map timelines do not display false
  timestamp precision or treat record validity as occurrence time.
- Historical records without provenance retain exact canonical bytes/digests.
  Existing evidence-linked map, claim, identity and relationship anchors still read.
- Oversized or malformed metadata, instruction-like text and cancellation obey
  existing input bounds and private-input rules. No private upload content becomes
  an unsolicited public search query.

## Separate unfinished requirements

Arabic/Persian PDF shaping, multilingual OCR, automatic transliteration quality,
additional calendar conventions and independent human semantic evaluation remain
separate work. This proposed delivery must not be represented as completing them
or as completing the full research expansion plan.
