# Source size and responsibility boundaries

Handwritten Python, TypeScript, JavaScript and CSS have a 350-line target and
a 400-line hard maximum. Count physical lines, including comments and blanks.
Do not compress formatting, remove useful documentation or lower test coverage
to fit. Split along an independent responsibility when that makes the code
easier to understand. A reviewed target exception never permits a file over 400.

Run `python scripts/check_file_length.py` from any working directory. CI and
pre-commit use this same command. It scans backend source and tests, frontend
source and scripts, root scripts and their tests, and executable frontend
configuration. CSS uses exactly the same thresholds as the other source files.
Warnings remain visible even for the reviewed exceptions below.

The existing exclusions remain narrow:

- Generated `*.gen.ts` and declaration-only `*.d.ts` files are outside this
  executable-source check. Regenerate the former; keep handwritten declarations
  small and review them normally.
- `frontend/src/components/brand/EvilEye.tsx` is the preserved third-party brand
  component. Do not split or redraw it as a line-count exercise.
- Dependency environments and bytecode caches are not repository source.
- JSON catalogues, generated OpenAPI, lockfiles, documentation and declarative
  YAML/TOML configuration have different review units. They are inventoried
  separately below when relevant; this does not exempt embedded scripts from
  normal correctness and security review. Move substantial executable workflow
  logic into checked scripts rather than accumulating it in YAML.

## CSS policy

Keep selectors with the component or presentation responsibility they style.
Import related files through the existing stylesheet entry point so callers
still load the complete component. Preserve import and rule order, specificity,
custom-property scope, media conditions and reduced-motion rules when moving
CSS. An `@import` belongs before ordinary rules; changing cascade layers is a
separate behavioural change.

KAN-232 divides `reportReader.css` into paper/layout, evidence/judgements and
tables/figures, with motion, responsive and print overrides last in the original
entry point. `eyeAssistant.css` imports the panel layout and saved-chat controls
before its composer and responsive rules. These are contiguous moves, preserving
the complete original declaration stream in order. No selectors were renamed.

## Reviewed target exceptions

Inventory basis: commit `47a76fa118e12640aaa8e36c1e9ba1cdc70e4ebc`, reviewed for
[KAN-232](https://alex-orr.atlassian.net/browse/KAN-232) on 10 October 2026. There
were 17 Python/TypeScript files above 350, all below 400, and two CSS files above
350. The schedule mapping and CSS splits below remove three of these entries.
Counts describe this snapshot, not an assertion about every later branch.

The combined KAN-216 inventory at `13872fc0` was checked on 10 October 2026.
Thirteen files retain a target exception for the stated responsibility. The
security transport and commercial-policy changes resolved three more entries,
listed below. The checker reports no file above the hard maximum.
Reassess the exception on the next substantive edit. Adding another independent
responsibility requires a split; the named future boundaries are guidance, not
permission to grow to 400. No exception suppresses checker output.

| File | Lines | Reason to retain the current boundary; next split if it grows |
| --- | ---: | --- |
| `backend/src/ase/adapters/store/memory.py` | 357 | One store owns the event map, secondary indexes, byte accounting, generation and eviction announcements. Insert/remove/update must change those together. Query readers and retention budgets are already separate. A future index extraction must own all corresponding mutations, not split methods across mixins. |
| `backend/src/ase/application/report_jobs/service.py` | 370 | Admission and explicit job controls share the source guard, authorisation, unit of work and release ordering. Preparation, control predicates, listing and release helpers are already separate. A future command service must preserve one transaction owner rather than distribute commits among helpers. |
| `backend/src/ase/application/reports/sections/runner.py` | 379 | One resumable run owns its completed topics, split-leaf count, rejection state and cumulative draft usage. Planning, contracts, prompts, assembly and synthesis are already collaborators. Keep checkpoint transitions and cancellation visible together; review a step-execution collaborator before adding another execution phase. This is the closest retained file to the ceiling. |
| `backend/src/ase/application/research/source_allocator.py` | 356 | One deterministic allocation pass produces choices and explanatory receipts from the same ranked pool and reservation accounting. Policy constants and result types are separate. Split pure candidate ranking if scoring expands, keeping selection and its receipts in the same pass. |
| `backend/tests/test_conflict_screening_model.py` | 360 | The canned screening batch and gateway fixture exercise the same model boundary: identity/quote validation, bounded input, cancellation and usage failures. Keeping the adversarial variants together makes the release conditions auditable. Split response-contract cases from async gateway behaviour if another model workflow is added. |
| `backend/tests/test_public_figures.py` | 371 | The small synthetic roster is checked from validation/import through matching, placement and API projection. The fixture links explain why the board receives each figure. Extract roster-builder tests and their fixture together if the import format changes; do not duplicate the roster setup. |
| `backend/tests/test_report_job_snapshots.py` | 366 | Paired freeze/restore tests compare immutable scope, provenance and historical compatibility using one snapshot fixture. Keeping rejected payload variants beside accepted round trips makes silent field loss visible. Extract scheduled-update snapshot cases if that payload evolves separately. |
| `backend/tests/test_source_allocator.py` | 363 | One controlled capability/profile inventory exercises ranking, exclusion receipts and overlapping reservation caps. The same fixture lets expected choices be compared across modes. Extract reservation-policy scenarios when adding another selection phase, with the shared fixture in one support module. |
| `backend/tests/test_subscription_schedule_time.py` | 353 | These integration cases follow scheduled time from DST resolution to overdue admission and baseline coverage. Shared clock, edition and capacity fixtures expose interactions rather than mocking the scheduler. Split outage/baseline cases if that recovery policy grows. |
| `backend/tests/test_ukraine.py` | 365 | The compact synthetic geography and claims fixtures connect imports, bounded collection, grouping and API projection for the Ukraine board. Preserve the fixture provenance chain. Split collector cases from board projection on the next provider extension. |
| `backend/tests/test_ukraine_figures.py` | 371 | Canned loss/civilian-impact data is validated from import to daily aggregation and provider-state projection. Assertions keep confirmed totals distinct from claims. Split provider acquisition tests if another provider is added, retaining aggregation cases with their shared source data. |
| `backend/tests/test_ukraine_reference.py` | 353 | The seed/catalogue fixture covers resolution, image constraints, validation and serving of the same bounded reference package. Split acquisition from catalogue-serving tests when either contract grows independently. |
| `frontend/src/lib/api/reports.ts` | 353 | This is the runtime validation boundary for a saved report, including its nested publication blocks, evidence and legacy optional fields. Other report contracts already have separate modules. Extract the publication-block schema if expanded, preserving the exported report schema and avoiding circular contract imports. |

## Resolved entries and other large files

| File at the inventory basis | Lines | Decision |
| --- | ---: | --- |
| `backend/src/ase/adapters/persistence/schedules.py` | 373 | Extract row/domain conversion into `schedule_mapping.py`. Leave repository transactions, worker authorisation and edition publication in the original module. Retain its existing internal conversion imports for current callers. |
| `frontend/src/features/reports/reportReader.css` | 636 | Split by presentation responsibility and enforce the common 400-line ceiling on every CSS file. |
| `frontend/src/components/assistant/eyeAssistant.css` | 361 | Split panel layout and saved chats from the composer, keeping the existing entry point and cascade order. |
| `backend/src/ase/adapters/feeds/http.py` | 356 | KAN-235 separates connection handling and preserves original TLS identity across pinned IP connections. The combined file is 287 lines. |
| `backend/src/ase/application/reports/fresh_web_research.py` | 352 | KAN-195 extracts commercial source admission into `web_research_admission.py`, retaining collection and cancellation ownership. The combined file is 343 lines. |
| `frontend/src/lib/map/MapLibreEngine.ts` | 353 | KAN-195 extracts the bounded spin lifecycle into `MapSpin.ts`, preserving engine revision and capture ownership. The combined file is 339 lines. |
| `.github/workflows/ci.yml` | 533 | Declarative pipeline configuration, outside the source-file limit. Job boundaries, dependencies and required gate names need their own review; no workflow change is part of KAN-232. |
| `frontend/src/lib/api/types.gen.ts` | 33,153 | Generated client contract, excluded. Reconcile from the combined backend schema during integration. |
| `frontend/pnpm-lock.yaml` | 5,328 | Dependency lockfile, excluded. Do not hand-split it. |

## Integration and ongoing review

Run the checker after combining concurrently developed branches and compare every
warning with this table. Update counts, remove resolved entries and review new
warnings. In particular, KAN-165 owns deployment script changes, KAN-221 changes
subscription outcome/version handling, and the active product/admin/release
worktrees were not modified here. Preserve those changes when reconciling the
schedule mapping or regenerated API. A passing check on this branch does not
certify a later combined checkout.

For a size-only extraction, use existing behaviour tests and compare moved code
or CSS in order before and after the change. New checker tests should prove its
thresholds and discovery boundaries, not duplicate every implementation detail.
