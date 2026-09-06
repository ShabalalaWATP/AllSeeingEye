# Report evidence assessment policy

Policy: `ase-evidence-v1`, 6 September 2026. This is an application policy informed
by public doctrine. It is not a NATO-prescribed aggregation algorithm, a calibrated
probability model or a complete implementation of PHIA analytical confidence.

## Four different questions

| Dimension | Question | Representation |
| --- | --- | --- |
| Source reliability | What is known about the source's reporting record? | A-F editorial metadata |
| Information credibility | How has this particular information been assessed? | 1-6 frozen item grade |
| Assessed likelihood | How likely is the judgement to be true or occur? | PHIA probability term proposed by the model |
| Analytical confidence | How sound and stable is the basis for that judgement? | Low/Moderate/High, constrained by an evidence ceiling |

These cannot be substituted for each other. Ten articles are not ten independent
observations, and “high confidence” does not mean “highly likely”. Source grades
are not numerical error rates and cannot be multiplied into a truth percentage.

The [PHIA uncertainty guidance, 24 March 2025](https://www.gov.uk/government/publications/explaining-uncertainty-in-uk-intelligence-assessment/explaining-uncertainty-in-uk-intelligence-assessment)
separates likelihood from confidence. Its confidence framework considers the
information base, analytical rigour, and complexity and volatility. The engine
primarily constrains the information base; its structural checks cannot establish
the soundness of an inference or a complete assessment of a changing environment.

[UK JDP 2-00, fourth edition, August 2023](https://assets.publishing.service.gov.uk/media/653a4b0780884d0013f71bb0/JDP_2_00_Ed_4_web.pdf),
paragraphs 3.39-3.40 and Table 3.1 (printed pages 58-60), describes separate
reliability and credibility evaluations and the NATO intelligence grading system.
It explicitly allows reliable sources to be wrong and unreliable sources to
provide credible information. F and 6 denote insufficient grounds to judge,
rather than falsehood. Paragraphs 3.47-3.48 distinguish the PHIA yardstick from
analytical confidence. The application is doctrine-informed, not accredited.

## Contribution matrix

Each frozen item receives an indicative contribution tier based on its two grades.
The tier describes what the recorded grades permit the engine to count. It does
not verify the source, the information, or its relevance to a particular claim.

| Source reliability | 1: confirmed | 2: probably true | 3: possibly true | 4: doubtful | 5: improbable | 6: cannot judge |
| --- | --- | --- | --- | --- | --- | --- |
| A | Strong | Strong | Moderate | Limited | Limited | Unassessed |
| B | Strong | Strong | Moderate | Limited | Limited | Unassessed |
| C | Moderate | Moderate | Limited | Limited | Limited | Unassessed |
| D | Moderate | Limited | Limited | Limited | Limited | Unassessed |
| E | Moderate | Limited | Limited | Limited | Limited | Unassessed |
| F | Moderate | Moderate | Limited | Limited | Limited | Unassessed |

F is deliberately not treated as the next step below E. Confirmed information
from a poor or unknown source remains useful, although a high-confidence ceiling
requires stronger recorded provenance. “Unassessed” items remain visible and may
be valuable leads; a quantity of them cannot establish corroboration.

The automatic live grader does not produce credibility 1 merely because headlines
look similar. Instrument/authoritative-source metadata can produce provisional 2,
with an explicit unverified rationale. A label of “strong” in this matrix is
therefore conditional on that recorded grading, not proof of independent checking.

## Combining evidence for one judgement

Only the judgement's cited support and opposition affect its ceiling. Unrelated
selected evidence cannot improve or suppress that ceiling.

1. Resolve labels to frozen items. Invalid citations remain validation findings.
2. Fold declared parent organisations and possible copies into groups. Use the
   translated title where available, retain the original, and use stable ordering.
3. Take the strongest eligible contribution in a group. Do not add the same
   group's strength repeatedly. Unknown provenance does not create corroboration.
4. Compare the strongest supporting and opposing contributions, keeping their
   labels and groups visible. More weak articles do not outvote stronger evidence.
5. Constrain the proposed confidence; never promote it automatically. Record the
   final confidence after optional devil's advocacy.

Single strong support can permit a Moderate ceiling. Multiple known groups with
Moderate-or-stronger support can also permit Moderate. Limited or unassessed
padding cannot raise it. High requires at least two distinct known groups with
strong credibility-1 support and no relevant flags or opposing evidence. These
are conservative product limits, not sufficient proof of analytical confidence.

Opposition at least as strong as support constrains the ceiling to Low. Weaker
opposition remains visible and prevents a High ceiling. An absence of cited
opposition means that the model supplied none, not that a comprehensive search
established consensus. Supporting/opposing relationships are model-assigned;
the engine has not verified whether the excerpts substantiate them.

## Worked expectations

| Inputs assigned to a judgement | Expected consequence |
| --- | --- |
| One A2 supporting source | Strong graded contribution; at most Moderate confidence |
| One A2 plus three E6 supporting items | Same ceiling; weak padding adds no corroboration |
| One A2 support and three E6 opposing items | Stronger support; opposition still visible; at most Moderate |
| One A2 support and one B2 opposing item | Comparable strong opposition; Low ceiling |
| Three E6 items and nothing stronger | Unassessed support; Low ceiling |
| Two F1 items from known different organisations | Useful Moderate contributions; no automatic High |
| Reprints across different outlets | Possible copies folded; not separate confirmation |
| Strong support plus unrelated weak items for other judgements | Supporting judgement's ceiling unchanged |
| Model proposes Low despite stronger support | Final confidence stays Low |

The count of articles can increase information coverage, but the app cannot claim
a corresponding increase in the likelihood of truth. Source access, underlying
attribution, relevance, contradictions and topic expertise still matter.

## Storage, outputs and retrieval

The assessment is engine-authored and saved with the report version in the
existing analysis JSON. It records its method version, item/group evaluations,
judgement explanations, final confidence, suggested improvements and validation
counts. The model cannot write the assessment object. No migration or durable
live-event archive is needed.

New assessments are produced after optional advocacy. Historical reports without
this field display “not recorded”; they are not regraded on read. Archiving links
and exporting a report retain its saved assessment. The reader, Markdown, PDF
and DOCX use that same data.

Retrieval remains distinct from assessment. Selection favours relevant varied
reporting within its bounded budget, shares caps across declared parent feeds,
defers repeated titles/content and breaks ties deterministically. Deferred items
remain available as backfill; similar wording is not a reason to discard possible
counterevidence. Recency and severity influence retrieval priority, not a numerical
confidence or truth score.

## Remaining improvements

- Record source-rating basis, subject expertise, primary/secondary status and
  review dates, rather than imply the current editorial metadata is measured.
- Add bounded on-demand API/feed research and explicit collection coverage.
- Record original attribution where available and verify passage-level support.
- Evaluate contradictions, alternative explanations and topic volatility with a
  labelled corpus before making stronger automated claims.
- Calibrate predictions only against well-defined dated outcomes, retaining the
  original forecast and separating probability calibration from evidence quality.

These are follow-ups, not capabilities created by a scoring matrix. The
[PHIA analytical standards](https://www.gov.uk/government/publications/phia-common-analytical-standards/phia-common-analytical-standards)
also emphasise auditable reasoning, contrary information and clear uncertainty;
those require more than source counts.
