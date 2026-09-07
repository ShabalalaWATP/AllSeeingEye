import type { AnnotationComparison, ComparisonSide } from '@/lib/api/annotationComparisons';
import { ComparisonAnnotations } from './ComparisonAnnotations';
import { ComparisonConfidence } from './ComparisonConfidence';
import { comparisonReportHref, ComparisonEvidenceLinks } from './ComparisonEvidenceLinks';
function Side({ value, name }: { value: ComparisonSide; name: string }) {
  return (
    <section className="space-y-2 text-xs [overflow-wrap:anywhere]">
      <h4 className="font-medium">{name}</h4>
      <a className="text-ember underline" href={comparisonReportHref(value)}>
        {value.title}, version {value.version_number}
      </a>
      <p>Version ID {value.version_id}</p>
      <p>Version created {value.version_created_at}</p>
      <p>
        Collection period {value.period_from ?? 'not recorded'} to{' '}
        {value.period_to ?? 'not recorded'}; data cutoff {value.data_cutoff ?? 'not recorded'}.
      </p>
      <details>
        <summary>Frozen content and evidence digests</summary>
        <p>Content {value.content_sha256}</p>
        <p>Evidence {value.evidence_sha256}</p>
      </details>
    </section>
  );
}
export function AnnotationComparisonResult({ value }: { value: AnnotationComparison }) {
  return (
    <section
      aria-label="Frozen annotation comparison"
      className="space-y-6 border-t border-line pt-4"
    >
      <h2 className="font-semibold">Frozen comparison</h2>
      <p className="text-sm text-muted">
        Selected before and selected after describe your chosen direction, not inferred chronology.
        Comparison generated {value.generated_at}; this is not source-valid or observation time.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        <Side value={value.before} name="Selected before" />
        <Side value={value.after} name="Selected after" />
      </div>
      <p className="text-xs [overflow-wrap:anywhere]">
        Compared by {value.compared_by}. Comparison method {value.method_version}. Digest{' '}
        {value.comparison_sha256}
      </p>
      <ComparisonAnnotations value={value} />
      <section aria-label="Frozen evidence changes" className="space-y-3">
        <h3 className="font-semibold">Frozen evidence changes</h3>
        <p className="text-sm text-muted">
          Evidence correspondence uses both source and event ID. Matching records does not establish
          identity or annotation continuity. Absence on a selected side can reflect collection
          limits.
        </p>
        {value.evidence_changes.length === 0 && <p>No evidence differences recorded.</p>}
        {value.evidence_changes.map((item, index) => (
          <article className="border-t border-line pt-3 text-sm" key={index}>
            <p>
              {item.source_id} / {item.event_id}: {item.status}
            </p>
            <p>
              Selected before:{' '}
              <ComparisonEvidenceLinks
                side={value.before}
                name="Selected before"
                labels={item.before_label ? [item.before_label] : []}
              />
            </p>
            <p>
              Selected after:{' '}
              <ComparisonEvidenceLinks
                side={value.after}
                name="Selected after"
                labels={item.after_label ? [item.after_label] : []}
              />
            </p>
            <p>{item.changed_fields.map((field) => field.replaceAll('_', ' ')).join(', ')}</p>
          </article>
        ))}
      </section>
      <ComparisonConfidence value={value} />
      {value.correspondences.length + value.judgement_correspondences.length > 0 && (
        <details>
          <summary>Preserved operator correspondence declarations</summary>
          {[...value.correspondences, ...value.judgement_correspondences].map((pair, index) => (
            <p key={index} className="text-sm whitespace-pre-wrap">
              {pair.rationale}
            </p>
          ))}
        </details>
      )}
      <ul className="list-disc pl-5 text-sm text-muted">
        {value.limitations.map((text, index) => (
          <li key={index}>{text}</li>
        ))}
      </ul>
    </section>
  );
}
