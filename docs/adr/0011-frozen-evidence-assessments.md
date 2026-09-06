# ADR 0011: freeze a qualitative evidence assessment per judgement

Status: accepted, 6 September 2026.

## Context

The report confidence guard ignored source reliability, rewarded weak padding and
applied a pool-wide ceiling to individual judgements. Alex requested automated
research reports that weigh source quality, corroboration and disagreement using
the relevant UK/NATO distinctions. Team operations are not the product priority.

## Decision

Apply the versioned qualitative policy in [REPORT_EVIDENCE_SCORING.md](../REPORT_EVIDENCE_SCORING.md).
Keep source reliability, information credibility, assessed likelihood and analytical
confidence separate. Use the strongest eligible item in each declared organisation
or possible-copy group, account for model-cited opposition, and never raise a
model's proposed confidence. Unknown provenance cannot supply corroboration.

Persist an engine-authored assessment after optional advocacy in the existing
report-version analysis JSON. The strict model response schema cannot supply it.
Expose a typed optional assessment and a current-methodology endpoint. Read and
export saved assessments without recomputing them, including during archiving.
Versions without an assessment remain explicitly without one. No schema migration
or durable raw-event archive is introduced.

## Consequences

One strong graded contribution can outweigh several weak reports, while source
count alone cannot manufacture confidence. Each judgement has inspectable reasons,
limits and improvement suggestions. Historical scores remain reproducible under
the recorded policy and are not silently changed by software upgrades.

The rules are application heuristics, not measured error rates, an official NATO
aggregation algorithm or complete PHIA analytical confidence. Source grades are
editorial/provisional metadata; support/opposition are model-assigned; source
independence and passage entailment remain unverified. The UI and exports must
retain these limits. New collection and evaluation capabilities require separate
implementation and evidence before claiming stronger assurance.
