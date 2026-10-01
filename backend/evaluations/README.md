# Real-model evaluation harness

This harness exercises the application's `Producer`, conservative grading, evidence selection and freezing, report prompt and JSON schema, draft retry, validator and frozen assessment. It supplies synthetic events and records usage in memory. It does not open the operator database, saved profiles or `.env`, start collectors, archive URLs, install a model or call one during fixture validation.

The eight cases are fictional and representative of failure modes, not a representative sample of world events. Their labels and reference rubrics were written by an assistant from the fixture definitions. They have **not been validated by a human**. A model passing these cases is not evidence of general factual accuracy, source independence, doctrine certification or readiness for autonomous publication.

## Where the cases live

The eight core cases and twelve regional seed cases are packaged with the
application under `src/ase/resources/evaluations/core` and
`src/ase/resources/evaluations/regional`, read through `importlib.resources`.
The CLI defaults to the packaged core casebook; pass
`--cases-dir ../backend/src/ase/resources/evaluations/regional` (or the path from
your working directory) for the regional seeds. Moving the files did not change
any case content or case fingerprint; `tests/test_evaluation_casebooks.py` pins
them. The two research replay cases stay in `evaluations/research_cases` and the
V01 contract corpus stays in `evaluations/v01`; neither is run from the app.

The harness modules (`casebook`, `replay`, `metrics`, `human_review` and
`pipeline`) now live in `ase.adapters.evaluations`. The `evaluations.*` modules
of the same names re-export them, so existing commands and imports still work.

Administrators can also run a selected subset of the packaged cases from
**Administration, Evaluations** against a saved AI connection. That path is
described in [docs/AI.md](../../docs/AI.md); it uses the stored connection
without copying credentials into files, meters every call through the AI
allowance ledger and keeps the same no-secrets rules for its download.

## Offline checks

From `backend`:

```powershell
uv run python -m evaluations validate
uv run pytest tests/test_evaluations.py --no-cov
```

Cases cover conflicting source claims, unknown provenance, syndicated copies, French negation, a retrospective date misreading, German numeric conventions, corrected casualty figures and missing hospital coverage. `reference` objects are withheld from the model. Frozen evidence includes original and unverified translated headlines so the model is tested against the information the application actually supplies.

## Run against an actual configured profile

Copy `evaluations/example-profile.json` to a new JSON file. Manually copy the base URL, exact installed model identifier, token limit and temperature from the intended app profile. The example identifier is a placeholder. Do not put credentials or encrypted app-profile fields in this file. The harness deliberately does not discover or decrypt operator configuration.

If the endpoint needs authentication, set `ASE_EVAL_API_KEY` in the current process environment using your normal secret-management workflow. This is the only environment setting read by the harness; it is never included in output artefacts. Empty keys are supported for local endpoints that do not require authentication.

Executing `run` makes real requests to the chosen endpoint. This was not executed against a live model while building the harness. No Ollama command was found on the development host's PATH during the read-only check, so its `/api/tags` endpoint was not probed and no model was downloaded.

```powershell
uv run python -m evaluations run --profile evaluations/local-profile.json --case conflicting_reports --max-calls 2 --out evaluations/runs/first-check
uv run python -m evaluations run --profile evaluations/local-profile.json --max-calls 16 --out evaluations/runs/full-assessment
```

Output directories must be new. Calls are serial and each has a timeout. The global call limit includes unsuccessful calls and validation retries. The ordinary `intrep` pipeline uses up to two drafting calls per case. Setting `direction` to true uses the app's `ask` product and direction stage. Setting `advocacy` to true enables the existing devil's advocacy stage. Those optional stages use the same supplied model profile and need a larger global call allowance. Token usage may be unavailable from some endpoints; missing counts are not reported as zero.

Each run writes `results.json`, a Markdown report per case, and `review.json`. Results include case fingerprints, actual prompts, model responses and the app's final validated output so retries or citation removal cannot hide raw-output defects. Keep these artefacts together. Output files are local and `evaluations/runs/` is ignored by git.

On an exception or cancellation, `results.json` retains completed cases and all
recorded model calls, including the unfinished case. Its status is `interrupted`
and `active_case` identifies the unfinished case. Arbitrary exception messages
are not saved. Completed runs have status `completed`; an interrupted run is
not a complete evaluation sample. A process kill or filesystem failure can still
prevent the final checkpoint from being written.

## What the measurements mean

Deterministic metrics check whether citation labels resolve, how many statement fields lack supporting citations, whether specified evidence was selected or referenced, declared organisation grouping and validator findings. A resolving label does not mean the cited item supports the claim. Counterevidence reference recall is measured in any citation role because a correction can become supporting evidence for a revised judgement. It does not establish that the model addressed the contradiction adequately. Null ratios mean there was no applicable denominator, not a perfect score.

`review.json` leaves every semantic label null. A human reviewer should read the original evidence, reference rubric and full report, provide their name or pseudonym, and label:

- Whether each statement field is supported, including numbers, dates, attribution and warranted inference. These fields can contain multiple propositions, so mark false if any factual claim or inference is unsupported.
- Whether each citation actually supports or contradicts as the report declares.
- Whether the case's counterevidence and required caveats are addressed adequately.

Leave uncertain or unreviewed fields null and explain disagreements with the fixture rubric in notes. The fields cover judgements, reporting items, assessment sections and alternative hypotheses. They do not automatically atomise claims or score every other piece of report prose. A reviewer can assess a subset; coverage and denominators remain explicit.

```powershell
uv run python -m evaluations score --results evaluations/runs/first-check/results.json --review evaluations/runs/first-check/review.json --out evaluations/runs/first-check/human-metrics.json
```

Scoring rejects mismatched run, case or statement fingerprints, duplicate labels and non-boolean semantic values. Its outputs are explicitly attributed to **self-declared human review**. The harness cannot authenticate the reviewer or turn assistant-written references into human labels. Unsupported-statement rates and citation relationship correctness remain separate from structural checks, with no aggregate “accuracy” number.

## Human citation verdicts from saved reports

Reviewers can record whether each model citation in a saved report supports its
judgement ("supports", "partly supports", "does not support" or "cannot tell") from the
report reader, and download that version's verdicts as JSONL. This is a different
dataset from the `review.json` labels above: those label synthetic evaluation runs,
while these come from real saved application reports. Both are human opinions, not
ground truth, and neither is authenticated beyond the application account that
recorded it.

```powershell
uv run python -m evaluations verdicts --export verdicts-a.jsonl --export verdicts-b.jsonl --out evaluations/runs/verdict-metrics.json
```

The reader refuses a file whose header is not `ase-report-citation-verdicts-v1`, whose
row count differs from its header, whose rows belong to another report version, whose
excerpt hash or offsets do not match the excerpt text, or whose `binding_sha256` no
longer matches the exact-version, judgement and excerpt fields. The same verdict
exported twice is merged by its id; conflicting copies are refused. It counts each
reviewer's latest verdict per citation, overall and by relation, every count with its
denominator, plus citations with a "does not support" verdict and citations where
reviewers disagree. No single accuracy figure is computed.

## Automated research replay

An optional replay mode exercises the production private collector, request
budgets, direction, initial draft, detailed challenge and possible redraft. Its
providers return explicit synthetic packets rather than make HTTP requests.
Initial and challenge packets are defined separately from reference rubrics;
counterevidence is not silently inserted into the initial evidence store.

Copy `example-research-profile.json`, supply the intended endpoint and model, and
use the separate research casebook:

```powershell
uv run python -m evaluations validate --cases-dir evaluations/research_cases
uv run python -m evaluations run --profile evaluations/local-research-profile.json --cases-dir evaluations/research_cases --max-calls 24 --out evaluations/runs/research-check
```

The run command makes real model calls. Validation and scripted tests do not.
The two assistant-authored scenarios cover later-discovered correction evidence
and unavailable collection. Neither has been human validated. `research_mode`
accepts `quick` or `detailed`; omit it for the original fixed-packet workflow.
Enable `direction` and `advocacy` to provide the model roles used for planning
and detailed challenge. Every selected research case must declare a replay
scenario, checked before constructing a gateway or creating output.

Outputs retain provider calls, query terms and languages, collection receipts,
challenge decisions, citation checks and evidence context. Replay packets are
returned independently of query relevance: this does not measure live retrieval,
source availability or the effectiveness of generated search terms. Human review
must still assess the model's reasoning and treatment of new evidence.

Raw citation-reference validity is unscored in replay mode because labels can
refer to different evidence after redrafting. The recorded prompts and responses
allow review against each draft's own packet; final citation-reference checks
remain available. This avoids comparing an earlier answer with the wrong packet.

## Integration boundary and remaining validation

`ase.adapters.evaluations.pipeline.evaluate_case(case, profile, recording_gateway, api_key)` (also importable as `evaluations.pipeline.evaluate_case`) is the reusable integration hook. Tests pass a scripted gateway through the same `Producer`; actual runs use the existing `OpenAiCompatibleGateway`. The default evaluates synthesis from a fixed packet; optional replay additionally exercises automated research stages. Neither evaluates live retrieval completeness, translation generation, auth, source availability, report persistence or browser behaviour. Real-model results and human semantic labels are still required; unit-test success only verifies the harness and its accounting.
