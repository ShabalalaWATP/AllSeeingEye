# Alert explanations, dispositions and hourly baselines

These capabilities extend the Alerts page at `/warning`. They do not change
frozen reports or infer research accuracy from software test results.

## Explain with Ask Eye

An alert explanation reads the alert under current personal/team access and
looks up only its retained event references. It displays the original matched
count, stored sample size and number of usable records included in the packet.
Alerts retain at most 20 references, so a firing with hundreds of matches does
not supply hundreds of observations to the model.

The packet contains current live records. Corrections since firing may change
their contents; this is not an immutable historical snapshot. Missing,
source-disabled, unsafe or size-limited records are described as unavailable,
without guessing that they expired. A notification without usable references
returns an unavailable-context message before routing or calling a model.

The selected alert's authorised team/owner determines provider routing; the
requesting account and alert team determine allowance accounting. Source status,
session validity and alert access are checked again before release. Citations
must reference records actually included in the bounded packet. Explanations
do not create a global-map continuation that could bypass alert access.

The final source-admission read precedes the application access check. The HTTP
release boundary also rechecks the alert under the administration lock after its
own source read, retaining that lock through the final session confirmation and
response construction. Regression tests revoke team membership during each of
those final source reads and require refusal of the completed private answer.

## Shared dispositions

The first acknowledgement may include `useful`, `noise` or `duplicate`, plus an
optional plain-text note of up to 200 characters. Existing acknowledgements
without feedback remain valid. A retry returns the retained first decision;
another teammate cannot silently replace it. Correction is not supported in
this version, and the UI explains that the shared decision is retained.

Rule feedback counts use UTC acknowledgement days: today and the previous 29
calendar days. This is a labelled calendar-day window, not a rolling 720-hour
interval. Each rule/day/disposition has a counter and the original owner/team
scope. The counter contains no report prose, note or event evidence. It survives
pruning of a raw alert that fired more than 30 days ago, then expires when its
acknowledgement day leaves the window. Deleted or inaccessible rules cannot be
queried. Notifications without a standing-rule ID do not contribute rule counts.

Acknowledgements retain existing current team-member write permissions and the
archived-team write restriction. Feedback never changes firing or cooldown.

## Ratio rules

`baseline_ratio` enables a ratio above 1 and at most 100. Ratio rules use a
one-hour match window and a configurable 7 to 30-day baseline, with the UI using
30 days. The existing threshold remains a minimum absolute count. Absolute-mode
rules retain their previous firing semantics.

Every enabled, authorised rule samples its current rolling one-hour match count
under kind `indicator` and its rule ID. Repeated samples in one UTC hour keep the
largest observed count. The historical mean therefore describes sampled hourly
maxima of rolling one-hour counts, not an uninterrupted census of complete hours.
Unsampled hours are not invented as zeros. The current hour is excluded from the
mean. A rule needs at least 168 sampled hours spanning seven days and a positive
mean before it can fire. A zero mean has no defined ratio and cannot trigger it.
The UI exposes this status; fired alerts preserve count, mean and realised ratio.

Matching-scope, category, keyword, severity, enabled-state or absolute/ratio-mode
changes reset the rule's samples in the same guarded transaction as the edit.
In-flight sampling rechecks the exact rule before writing, so samples from the
old semantics cannot reappear after reset. Renaming a rule preserves its cohort.

For 200 continuously enabled rules, 30 days require about 144,000 sample rows
(200 × 24 × 30), plus up to 200 for the current cutoff hour. Matching edits reset
their rows; indicator sampling prunes indicator rows beyond the retention bound.
All-kind baseline retention is supplied by the integrated KAN-28 parent. Its
activity hour/ID index supports bounded deletion batches across all sample kinds.

Migration `0070` refuses downgrade while a ratio rule remains configured or any
alert retains a baseline mean or ratio. Fired evidence must remain protected even
when its original rule has returned to absolute mode or has been deleted. Both
checks precede schema changes; a refusal preserves the stored data and revision.

## Validation limits

Tests use synthetic SQLite data, fake live events and fake model replies. They
cover access revocation, source changes, sample gaps, allowance refusal, invalid
citations, idempotence, shared acknowledgement, raw-alert pruning, counter expiry,
warm-up, cooldown and semantic resets. SQLite migrations are exercised and
PostgreSQL upgrade SQL is rendered. A live PostgreSQL migration and browser
acceptance have not been performed. No live model quality or production
performance claim follows from these checks.
