# KAN-194: catalogue provenance and check dates

Acceptance review found six source rows with no discovery link. They describe
mixed public evidence or private uploads, so a single provider licence URL would
misrepresent their provenance. The rows now link to the relevant catalogue,
reference data or source implementation at immutable revision
`99bff8f974c3712d99e6c0424c8685e42bb354fd`:

- `map:military_source_index`
- `reference:conflicts`
- `research-asset-register`
- `research-retained-area-feeds`
- `research_import`
- `research_media`

Each link is labelled `catalogue_provenance_only`. The catalogue was inspected on
10 October 2026, and the rendered register identifies that date as a catalogue
check with provider terms unverified. All six retain `per_item_required`, unknown
commercial/hosted rights, `licence_required`, and null terms-check and attempted
lookup dates. No provider permission or legal verification is inferred.

The strict metadata gate now rejects null, empty and non-HTTP source links. The
source register and generated public attribution data both contain the six links.
Structured comparison against the starting revision confirms that only these
rows' link, link-kind and catalogue-check fields changed. All 581 sources have a
link, and the 157 blocked/inconclusive source rows keep their existing attempted
dates and labels. Provider policy data is unchanged.

## Validation

- Before the change, six provenance cases and the null-link schema regression
  failed, while the attempted-date control passed (4.27 seconds). A separate
  renderer regression failed on the absent catalogue date (1.04 seconds).
- The final source-register and commercial-policy group passed all 51 cases in
  4.62 seconds. The tests block provider network connections.
- Both Node attribution tests passed, including generated-file freshness and
  preservation of unknown rights. Both documentation generators pass their
  freshness checks.
- Focused Ruff and formatting checks, strict mypy for the renderer and generated
  frontend JSON Prettier checks passed. Both frontend TypeScript configurations
  passed. Changed handwritten Python files contain 180, 225 and 281 lines, below
  the 350-line target.
- Independent read-only review found no actionable issue in provenance, date
  semantics, schema validation or preserved rights restrictions.

An additional Prettier probe of the backend metadata reports the same existing
style mismatch at the unchanged starting revision. Its established JSON layout
is retained to keep the patch limited to the six records; no formatter rule or
gate was changed. Generated frontend JSON passes its configured formatter.

Dependencies were installed privately, frozen and offline. Shared database
environment variables were cleared; no database service, browser, live provider,
email recipient or production setting was used. Coverage and full repository CI
were not rerun for this metadata/renderer follow-up. Provider permissions and
legal review remain separate from catalogue completeness.
