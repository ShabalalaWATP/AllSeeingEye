import type { CollectionContinuation as Review } from '@/lib/api/collectionContinuation';

const actions = {
  continue: 'Keep the original search plan',
  replan: 'Run a revised search within the remaining budget',
  sufficient: 'Stop collection after the evidence review',
};
const bases = {
  empty_results: 'The initial successful searches returned no additional evidence.',
  potential_conflict:
    'The model identified a possible conflict to investigate. This is not a verified contradiction.',
  question_addressed:
    'The model considered the question adequately covered. This is not a guarantee of completeness or truth.',
  insufficient_context: 'The available context did not justify stopping or revising the search.',
  invalid_or_unavailable: 'No valid review was available; the original scope remains in effect.',
};

export function CollectionContinuation({ value }: { value: Review }) {
  return (
    <section
      aria-label="Collection continuation decision"
      className="space-y-3 rounded border border-line p-3 text-xs"
    >
      <h3 className="font-medium text-text">Why collection continued or stopped</h3>
      <p className="text-cyan">{actions[value.decision]}</p>
      <p>{bases[value.basis]}</p>
      <p className="break-words" dir="auto">
        {value.rationale}
      </p>
      {value.override_reason && (
        <p className="text-amber">
          {value.requested_decision
            ? `Proposed action: ${actions[value.requested_decision]}. `
            : ''}
          Applied constraint: {value.override_reason}
        </p>
      )}
      <p className="text-muted">
        {value.context_count} of {value.total_count} first-pass records were included in the review.{' '}
        Model: {value.model || 'Not recorded'}. Exact excerpts establish where text came from; they
        do not establish source independence, claim accuracy or semantic agreement.
      </p>
      {!!value.gaps.length && (
        <div>
          <h4 className="font-medium">Declared gaps</h4>
          <ul className="list-disc space-y-1 pl-4">
            {value.gaps.map((gap, index) => (
              <li key={index} dir="auto">
                {gap}
              </li>
            ))}
          </ul>
        </div>
      )}
      {!!value.citations.length && (
        <details>
          <summary className="cursor-pointer py-2">Recorded review excerpts</summary>
          <ul className="space-y-3">
            {value.citations.map((citation, index) => (
              <li key={index} className="space-y-1">
                <p className="text-muted">
                  {citation.source_id} · original {citation.field}
                </p>
                <blockquote className="border-l-2 border-cyan pl-3" dir="auto">
                  {citation.quote}
                </blockquote>
                <p className="break-all text-muted">
                  Collected record: {citation.event_id} · content hash: {citation.content_hash}
                </p>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-muted">
            These are collected-record references. Report annex selection is a separate step.
          </p>
        </details>
      )}
    </section>
  );
}
