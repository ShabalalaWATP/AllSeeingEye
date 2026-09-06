# ADR 0009: Preserve uncertainty at the analysis boundary

Status: Implemented, 6 September 2026. Refines the corroboration and validation assumptions in [ADR 0007](0007-grade-before-generate.md).

## Context

The app grades live feed items before an LLM writes a report. Review found that headline similarity could promote opposing claims to “confirmed”, copied material could cause a source to corroborate itself, and descriptive metadata claimed independent sourcing and zero contradictions without measuring either. New model responses could omit the report body, invent displayed grades or receive a confidence ceiling justified by unrelated evidence. Requested report windows also diverged from the evidence window.

These are analysis-integrity failures even when authentication, dependency and syntax checks pass. The system must distinguish observations, heuristic inferences and unverified claims.

## Decision

1. Keep deterministic grading before generation, but treat topic similarity as a navigational relationship rather than proof of claim agreement. Do not create credibility 1, 4 or 5 from headline/place matches. Text without established support remains unassessed; instrument/authoritative metadata supports provisional grade 2. Negation/qualification cues request caution, not a verdict on truth.
2. Group declared parent organisations and possible copies transitively. Call these “declared organisation groups”, not measured independent reports. Unknown provenance cannot add a known organisation. New contradiction counts are null because automatic contradiction assessment has not run.
3. Validate new output strictly against the schema supplied to the model. Reject missing/unknown fields, wrong types and excessive sizes before tolerant domain construction. Keep tolerant historical/failed report decoding. Do not rewrite old evidence to imply current compliance.
4. Validate judgements against actual frozen support. Require known supporting evidence, unique identifiers and known assumption references. Unrelated selected evidence cannot raise a judgement's confidence ceiling. Render exact cited grades and generate the sourcing statement from body-cited evidence.
5. Distinguish model rationale from engine metadata. Safety ceilings are not calibrated confidence estimates or proof. `ready` means mechanical checks passed, not human approval or validated OSINT.
6. Use the requested window for selection and the header; persist current period metadata on regeneration. Freeze available translation/language, observation time, location precision and topic metadata with original snippets and hashes. Missing historical metadata remains unknown.

## Consequences

- More text items remain credibility 6 and many judgements receive Low or Moderate ceilings. This is expected without claim-level verification.
- Repetition, distinct outlet names and nearby sensor observations cannot silently become proof of attribution or agreement.
- Conservative copy grouping can combine genuinely separate reporting. It is a counting guard, not a finding of plagiarism or shared ownership.
- Strict validation can reject responses older code accepted. Failed and needs-review results remain inspectable; one retry can address concrete findings.
- Historical `ready` versions retain their original content and status. Reading them is compatibility, not retrospective validation.
- Citation existence and language checks do not prove entailment, factual accuracy, balanced collection or causal inference. Human review and deeper techniques remain separate product work.
- Normalised snippets and hashes preserve useful provenance, but do not constitute full-page preservation, authenticating signatures or forensic chain of custody.

## Verification and maintenance

Regression coverage must include affirmative/negative headline mixtures, syndication across organisations, unknown provenance, empty/malformed responses, truncation attempts, missing/duplicated support identifiers, frozen-grade discrepancies, per-judgement ceilings, requested-window overrides, regenerated period metadata and legacy deserialisation. Tests should assert honest uncertainty and retained provenance, not reward unsupported confidence.

Focused domain modules own similarity, clustering, source provenance, model-input validation and report support. Application orchestration supplies the requested window and frozen evidence. Exports consume saved versions. [The doctrine document](../03_DOCTRINE_AND_REPORTING.md) separates implemented behaviour from proposed verification and review capabilities.
