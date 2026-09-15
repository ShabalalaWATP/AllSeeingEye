# V01 synthetic contract corpus

This corpus contains 60 individually reviewable, assistant-authored synthetic cases:
ten each for conflict, cyber, economy, disaster/humanitarian, company/policy and
custom-area research. No packet is captured public evidence. No expectation is a
human label, and no current provider or model has been evaluated here.

The recorded local check results and remaining gates are in [VERIFICATION.md](VERIFICATION.md).

Each JSON case records its question, requirements, allowed country/area and time
window, public-information boundary, complete source packet, useful source IDs,
exact expected passages and source-version hashes, reference outcome, pitfalls,
acceptable abstentions and questions for an analytical reviewer. Names, statements,
source organisations, origins and coordinates are invented for local tests. The
`example.invalid` URLs identify fixtures and are never retrieval targets.

The six domains share ten adversarial families, with domain-specific claims,
units, date precision, privacy and geographic limits. This tests portability of
bounded contracts across domains. It does not provide 60 statistically independent
failure modes or a representative estimate of analytical performance.

## Frozen split and source identity

The manifest fixes 48 development cases (01–08 in each domain) and 12 held-out
regression cases (09–10). Linked subscription pairs stay in the same split. The
split was fixed before any production ranking or prompt tuning for this corpus;
this task performs no such tuning. The same assistant authored both sets and the
held-out files are visible. This is not blinded validation or independent review.

The loader checks manifest paths, file sizes, file hashes, packet-content hashes,
reference passages, exact source versions, domain counts, split counts and shared
edition consistency. A digest detects changes against the checked-in manifest;
it is not a signed attestation. Deliberate changes require review of both case and
manifest changes. Do not regenerate held-out expectations merely to make a changed
production policy pass.

## What the offline runner measures

The runner calls existing production functions, with expectations supplied only
to the scorer:

| Contract | Production function | Denominator |
| --- | --- | --- |
| Exact excerpt presence | `exact_excerpt` | 12 positive/negative proposals |
| Retained excerpt offsets | `exact_excerpt` | 6 returned excerpts |
| Literal mismatch indicators | `mismatch_indicators` | 18 date, negation and unit probes |
| Publication-time admission | `evidence_matches_time` | 12 timed records |
| Point inclusion in an area | `BoundingBox.contains` | 2 antimeridian-area points |
| Edition state and reason/identity fields | `classify_research_change` | 24 consecutive pairs per field |

The 24 comparison cases include explicit same-URL corrections, syndicated copies,
translated text, a quiet adequately covered edition, probability-only changes and
provider outages. Twelve held-out cases form six three-edition sequences: a
likelihood-only change followed by failed acquisition. Shared editions and their
source versions must agree across adjacent cases.

Synthetic projection change precision uses true positive structured changes over
all classified material changes. Recall uses the same numerator over reference
material changes. There are 12 positive pairs in this corpus. These measurements
do not assess extraction of claims from model prose or human judgement of material
change. The no-data metric checks the classification of six failed-acquisition
pairs; it does not assess whether a generated report explains that gap.

False units deliberately produce no literal indicator in six cases. This records
a known boundary of the production check, not six correct analytical answers.
Similarly, a translated version can be structurally novel while sharing an origin.
Neither a new content hash nor a new URL establishes independent corroboration.

Results include counts and denominators per domain and **declared** depth. Depth
labels describe case intent; no depth-specific planner runs here. Empty denominators
produce `null`, never zero or perfect accuracy. Required-question coverage, curated
retrieval recall, semantic support, factual date/attribution/number accuracy,
counterevidence retention, analytical abstention and human change quality remain
explicitly unmeasured. The privacy, authorisation, budget and duplicate-publication
paths require their separate production integration suites.

Function timings exclude providers, models, persistence and the UI. External
requests, model calls and external API cost are known zero. Local CPU cost is not
estimated. Do not use these timings as an end-to-end performance baseline.

## Run locally

From `backend`, these commands do not load settings, credentials, databases or
provider/model adapters:

```powershell
uv run python -m evaluations.v01 validate
uv run python -m evaluations.v01 contracts --split development --out C:/Temp/v01-development.json
uv run python -m evaluations.v01 contracts --split held_out --out C:/Temp/v01-held-out.json
```

The destination parent directory must already exist. Output files are created
exclusively and are never overwritten. The contract command returns a non-zero
status if a reference expectation fails. Omitting `--out` writes JSON to stdout.

Before pytest, apply the process-local disposable SQLite preflight from packet 7,
including clearing token-race and PostgreSQL test URL overrides. Then run:

```powershell
uv run pytest tests/test_evaluation_v01_contracts.py tests/test_evaluation_v01_integrity.py --no-cov -q
uv run ruff check evaluations/v01 tests/test_evaluation_v01_contracts.py tests/test_evaluation_v01_integrity.py
$env:MYPYPATH = 'src'
uv run mypy evaluations/v01 tests/test_evaluation_v01_contracts.py tests/test_evaluation_v01_integrity.py
```

The tests deny socket/HTTP access for contract execution and include wrong-reference
negative controls, source-version corruption, manifest tampering, path escape,
oversized inputs, partial dates, misleading evidence-origin labels and conflicting
shared editions. No application production module is changed by this harness.

## Remaining analytical review gate

The separate existing real-model harness remains under `evaluations/`; its live
run command is not invoked by this package. Before V01 analytical acceptance:

1. An identified reviewer must inspect the packets, reference outcomes, dates,
   units, origin assignments and synthetic limitations. Record their role, review
   date and case/manifest hashes. A source packet is reviewable without being reviewed.
2. Adapt the selected packets to the real collection and report-generation path,
   with a recorded current model configuration and bounded authorised run budget.
   Keep reference expectations out of model inputs. Record report/version/run IDs
   and exact statement/passage hashes before review.
3. Use `human_review_template.json` as an unfilled record outline. Record material
   statement support, qualification, date/attribution/number correctness, required
   question status, counterevidence, abstentions and changed-edition outcomes.
   Include reviewer identity and role, rationale and disagreements. Seek a second
   reviewer for consequential disagreements and retain both judgements.
4. Calculate the packet-7 acceptance measures with reviewed counts and denominators
   per domain and executed depth. Do not replace human labels with automated scores,
   silently omit failed cases or call the visible split independent validation.

Until those steps run, the human-reviewed quality and release gates are unverified.
