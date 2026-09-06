# Report assessment change review

Reviewed 6 September 2026 on `codex/report-evidence-scoring`. This note covers the
new frozen evidence policy, its API and report rendering. It is not a repeat of
the whole application ASVS review or a production release approval.

## Boundaries reviewed

- The assessment is generated in the domain/application pipeline. It is excluded
  from the strict model response schema, so a model cannot supply its own score.
- Assessment generation follows optional advocacy and precedes the existing late
  authorisation check. Existing report ownership/team checks protect saved values,
  comparisons and exports. The new methodology endpoint requires an active user
  and returns only shared policy metadata.
- Frozen JSON is decoded through explicit expected dataclass, enum and primitive
  types. It does not import classes named by data or evaluate expressions. Missing
  legacy values stay absent; malformed saved assessments fail rather than silently
  acquire a new score or coerce a misleading value.
- Markdown projection uses the existing text escaping; PDF/DOCX receive plain
  text and do not fetch remote content. React renders assessment strings as text.
  Methodology links retain protocol validation and safe external-link attributes.
- No dependency, credential, database migration, external collector or network
  permission was added. The selected evidence and assessment remain bounded by
  existing report limits; live events are not persisted.

## Verification

An independent review found no actionable scoring or persistence defect in its
scope. Counterexamples exercised strong support versus three weak opposing items,
weak and duplicate padding, unknown provenance borrowing a known source's status,
opposing evidence, order invariance and frozen JSON/legacy round-trips.

Focused tests verify authenticated methodology access, strict response schemas,
untrusted export text, historical persistence and archiving, final advocacy
confidence, failed/empty products and existing late-access behaviour. The report
assessment/export/production selection also passed 53 tests on a disposable
PostgreSQL 17.10 database. That container was removed and absence verified.

Ruff, mypy, import contracts, Bandit and all pre-commit gates including Gitleaks
passed. The final integrated suites passed 719 SQLite tests (two PostgreSQL-only
skips, 96.16 percent coverage) and 359 frontend tests (98.04 percent lines,
91.70 percent branches). Existing deployment gates and image findings in
[the base-image review](API_BASE_IMAGE_TRIAGE.md) remain separate; those images
were not rebuilt or rescanned by this scoring review.

## Analytical limitations

Mechanical guards cannot establish that a citation entails a claim, that source
chains are independent, or that collection was comprehensive. Current grades are
editorial/provisional metadata. The matrix is an explicit application heuristic,
not a statistical truth percentage or a complete PHIA confidence evaluation.
These limits are part of the saved assessment and the displayed method.
