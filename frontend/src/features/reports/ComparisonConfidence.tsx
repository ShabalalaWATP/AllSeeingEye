import type { AnnotationComparison, ComparisonSide } from '@/lib/api/annotationComparisons';
import { ComparisonEvidenceLinks } from './ComparisonEvidenceLinks';
function FrozenConfidence({
  side,
  id,
  name,
}: {
  side: ComparisonSide;
  id: string | null;
  name: string;
}) {
  const judgement = side.judgements.find((item) => item.id === id);
  const assessment = side.assessment?.judgements.find((item) => item.judgement_id === id);
  if (!judgement)
    return (
      <p className="text-sm text-muted">
        {name}: no corresponding judgement. No directional confidence change is inferred.
      </p>
    );
  return (
    <section className="space-y-3 text-sm" aria-label={`${name} confidence inputs`}>
      <h5 className="font-medium">
        {name}: {judgement.id}
      </h5>
      <p>{judgement.statement}</p>
      <p>Recorded confidence: {judgement.confidence}</p>
      <p>{judgement.confidence_statement}</p>
      {!assessment ? (
        <p className="text-muted">
          Frozen assessment unavailable. These inputs have not been recalculated.
        </p>
      ) : (
        <>
          <p>Method: {side.assessment?.method_version}</p>
          <dl className="grid grid-cols-2 gap-2">
            {[
              ['Final confidence', assessment.final_confidence],
              ['Confidence ceiling', assessment.confidence_ceiling],
              ['Support contribution', assessment.support_tier],
              ['Opposition contribution', assessment.opposition_tier],
              ['Balance', assessment.balance],
              ['Assessment status', assessment.status],
            ].map(([label, text]) => (
              <div key={label}>
                <dt className="text-muted">{label}</dt>
                <dd>{text?.replaceAll('_', ' ')}</dd>
              </div>
            ))}
          </dl>
          {assessment.explanation.map((text, index) => (
            <p key={index}>{text}</p>
          ))}
          <p>
            Supporting:{' '}
            <ComparisonEvidenceLinks
              side={side}
              labels={assessment.supporting_labels}
              name={name}
            />
          </p>
          <p>
            Opposing:{' '}
            <ComparisonEvidenceLinks
              side={side}
              labels={assessment.contradicting_labels}
              name={name}
            />
          </p>
          <details>
            <summary className="cursor-pointer">
              Frozen source grades and independence groups
            </summary>
            <div className="space-y-3 py-2">
              {side.assessment?.evidence
                .filter((item) =>
                  [...assessment.supporting_labels, ...assessment.contradicting_labels].includes(
                    item.label,
                  ),
                )
                .map((item) => (
                  <div key={`${item.source_id}:${item.event_id}`}>
                    <ComparisonEvidenceLinks side={side} labels={[item.label]} name={name} />
                    <p>
                      Source {item.source_id} / Event {item.event_id}
                    </p>
                    <p>
                      Reliability {item.reliability}; information credibility {item.credibility};
                      contribution {item.contribution}.
                    </p>
                    <p>Organisation: {item.organisation ?? 'Unknown'}</p>
                    {[...item.flags, ...item.reasons].map((text, index) => (
                      <p key={index}>{text}</p>
                    ))}
                  </div>
                ))}
              {(
                [
                  ['Support', assessment.support_groups],
                  ['Opposition', assessment.opposition_groups],
                ] as const
              ).map(([label, groups]) => (
                <div key={label}>
                  <h6>{label} groups</h6>
                  {Array.isArray(groups) &&
                    groups.map((group) => (
                      <p key={group.id}>
                        {group.id}: {group.labels.join(', ')}; {group.contribution}; corroborating{' '}
                        {group.corroborating_contribution}; known organisation{' '}
                        {String(group.known_organisation)}; possible copy{' '}
                        {String(group.possible_copy)}; confirmed strong{' '}
                        {String(group.confirmed_strong)}
                      </p>
                    ))}
                </div>
              ))}
            </div>
          </details>
          <ul className="list-disc pl-4">
            {assessment.limitations.map((text, index) => (
              <li key={index}>{text}</li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
export function ComparisonConfidence({ value }: { value: AnnotationComparison }) {
  return (
    <section aria-label="Confidence explanations" className="space-y-4">
      <h3 className="font-semibold">Confidence explanations</h3>
      <p className="text-sm text-muted">
        Observed differences in frozen inputs and outputs are not a probability of truth or proof of
        a unique cause. Judgement labels are local to each report. Different methods remain visible;
        old assessments are never recalculated here.
      </p>
      {value.confidence_changes.length === 0 && <p>No judgement assessments to compare.</p>}
      {value.confidence_changes.map((change, index) => (
        <article className="space-y-3 border-t border-line pt-3" key={index}>
          <h4 className="font-medium">
            {change.correspondence === 'unmatched'
              ? 'Separate, unmatched judgement'
              : 'Compared judgements'}
          </h4>
          <p className="text-xs text-muted">
            Correspondence: {change.correspondence.replaceAll('_', ' ')}
          </p>
          {change.explanations.map((text, i) => (
            <p key={i}>{text}</p>
          ))}
          {change.changed_fields.length > 0 && (
            <p>
              Observed differences:{' '}
              {change.changed_fields.map((field) => field.replaceAll('_', ' ')).join(', ')}
            </p>
          )}
          <div className="grid gap-4 md:grid-cols-2">
            <FrozenConfidence side={value.before} id={change.before_judgement_id} name="Before" />
            <FrozenConfidence side={value.after} id={change.after_judgement_id} name="After" />
          </div>
        </article>
      ))}
    </section>
  );
}
