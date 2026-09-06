import type { ReportAssessment } from '@/lib/api/reportAssessment';

export function ReportAssessmentSummary({
  assessment,
}: {
  assessment: ReportAssessment | null | undefined;
}) {
  return (
    <section aria-label="Evidence strength" className="border-y border-line py-5">
      <h2 className="text-base font-semibold">Evidence strength</h2>
      {assessment == null ? (
        <p className="mt-2 text-sm text-muted">
          Assessment not recorded for this version. Its evidence has not been reweighed.
        </p>
      ) : (
        <>
          <dl className="my-4 grid grid-cols-2 gap-x-5 gap-y-4 sm:grid-cols-4">
            {(
              [
                ['Supported', assessment.tallies.supported_judgements],
                ['Limited', assessment.tallies.limited_judgements],
                ['Contested', assessment.tallies.contested_judgements],
                ['Unsupported', assessment.tallies.unsupported_judgements],
              ] as const
            ).map(([label, count]) => (
              <div key={label}>
                <dt className="text-xs text-muted">{label} judgements</dt>
                <dd className="mt-1 font-mono text-xl">{count}</dd>
              </div>
            ))}
          </dl>
          {assessment.judgements.length === 0 && (
            <p className="mb-3 text-sm text-muted">
              No key judgements were recorded for assessment.
            </p>
          )}
          <p className="text-xs text-muted">
            {assessment.tallies.evidence_items} evidence items ·{' '}
            {assessment.tallies.declared_groups} declared organisation{' '}
            {assessment.tallies.declared_groups === 1 ? 'group' : 'groups'} ·{' '}
            {assessment.tallies.possible_copy_groups} possible-copy groups ·{' '}
            {assessment.tallies.unknown_provenance_items}{' '}
            {assessment.tallies.unknown_provenance_items === 1 ? 'item' : 'items'} with unknown
            provenance
          </p>
          <p className="mt-2 text-xs text-muted">
            Validation: {assessment.validation_errors} errors · {assessment.validation_warnings}{' '}
            warnings
          </p>
          <p className="mt-3 text-sm text-muted">
            Grades and supporting or opposing relationships are evaluated automatically. Source
            independence and whether a source establishes a claim remain unverified.
          </p>
          <p className="mt-2 text-xs text-muted">
            Unsupported means no assessed support. Unassessed information may still be useful; it is
            not treated as false.
          </p>
          <details className="mt-3 text-xs text-muted">
            <summary className="cursor-pointer py-2">
              Assessment limits · {assessment.method_version}
            </summary>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              {assessment.limitations.map((text) => (
                <li key={text}>{text}</li>
              ))}
            </ul>
          </details>
        </>
      )}
    </section>
  );
}
