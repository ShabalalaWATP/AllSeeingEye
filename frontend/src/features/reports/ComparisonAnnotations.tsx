import type { AnnotationComparison, ComparisonSide } from '@/lib/api/annotationComparisons';
import { annotationTitle } from './comparisonSelection';
import type { ComparisonAnnotation } from './comparisonSelection';
import { ComparisonEvidenceLinks } from './ComparisonEvidenceLinks';
export const describeComparisonStatus = (status: string) =>
  ({
    added: 'Selected only after',
    removed: 'Selected only before',
    changed: 'Changed',
    unchanged: 'Unchanged',
  })[status] ?? status;
function Revision({ side, id, name }: { side: ComparisonSide; id: string | null; name: string }) {
  const value: ComparisonAnnotation | undefined = [
    ...side.revisions,
    ...side.identity_revisions,
    ...side.relationship_revisions,
  ].find((item) => item.id === id);
  if (!value)
    return (
      <p className="text-sm text-muted">
        {name}: no revision selected. This is not a withdrawal decision.
      </p>
    );
  return (
    <section
      aria-label={`${name} exact revision ${value.number}`}
      className="space-y-2 text-sm [overflow-wrap:anywhere]"
    >
      <h5 className="font-medium">
        {name}: revision {value.number}
      </h5>
      <p>{annotationTitle(value)}</p>
      <p>{'state' in value ? value.state : value.disposition}</p>
      <p className="text-xs text-muted">
        Revision ID {value.id} / Author {value.authored_by} / {value.created_at}
      </p>
      <p className="whitespace-pre-wrap">{'reason' in value ? value.reason : value.rationale}</p>
      {value.unresolved_conflicts.length > 0 && (
        <ul className="list-disc pl-4">
          {value.unresolved_conflicts.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )}
      {'assertion' in value && (
        <details>
          <summary>Frozen source relationship</summary>
          <p>
            {value.assertion.kind} accounting-consolidation parent, not an ownership or identity
            determination.
          </p>
          <ComparisonEvidenceLinks
            side={side}
            labels={[value.assertion.evidence_label]}
            name={name}
          />
          <p>
            Captured {value.assertion.captured_at}; publication{' '}
            {value.assertion.published_at ?? 'not recorded'}. Period metadata:{' '}
            {value.assertion.periods_state}.
          </p>
          <p>Current validity is not inferred from capture or review time.</p>
          {value.assertion.periods?.map((period, index) => (
            <p key={index}>
              {period.type}: {period.startDate || 'Not recorded'} to{' '}
              {period.endDate || 'Not recorded'}
            </p>
          ))}
        </details>
      )}
      {'candidate' in value && (
        <p>
          Captured candidate:{' '}
          <ComparisonEvidenceLinks
            side={side}
            labels={[value.candidate.candidate.evidence_label]}
            name={name}
          />
        </p>
      )}
      {value.citations.map((citation, index) => (
        <blockquote key={index} className="border-l border-line pl-3">
          <ComparisonEvidenceLinks side={side} labels={[citation.label]} name={name} /> /{' '}
          {citation.relation} / Original {citation.excerpt.field}
          <p>{citation.excerpt.text}</p>
        </blockquote>
      ))}
      <details>
        <summary className="cursor-pointer">Exact frozen revision fields</summary>
        <pre className="whitespace-pre-wrap text-xs">{JSON.stringify(value, null, 2)}</pre>
      </details>
    </section>
  );
}
export function ComparisonAnnotations({ value }: { value: AnnotationComparison }) {
  return (
    <section className="space-y-4" aria-label="Annotation changes">
      <h3 className="font-semibold">Annotation changes</h3>
      <p className="text-sm text-muted">
        Only selected revisions are compared. Distinct roots are unmatched unless you explicitly
        declare a correspondence. A missing selection does not establish withdrawal or
        disappearance.
      </p>
      {value.annotation_changes.length === 0 && <p>No annotation revisions selected.</p>}
      {value.annotation_changes.map((change, index) => (
        <article key={index} className="space-y-3 border-t border-line pt-3">
          <h4 className="font-medium">
            {change.kind}: {describeComparisonStatus(change.status)}
          </h4>
          <p className="text-xs text-muted">
            Correspondence: {change.correspondence.replaceAll('_', ' ')}
            {change.correspondence === 'operator_declared'
              ? ' (operator judgement, not verified sameness)'
              : ''}
          </p>
          {change.changed_fields.length > 0 && (
            <p className="text-sm">
              Changed fields:{' '}
              {change.changed_fields.map((field) => field.replaceAll('_', ' ')).join(', ')}
            </p>
          )}
          <div className="grid gap-4 md:grid-cols-2">
            <Revision side={value.before} id={change.before_revision_id} name="Before" />
            <Revision side={value.after} id={change.after_revision_id} name="After" />
          </div>
        </article>
      ))}
    </section>
  );
}
