import type { ResearchPlan } from '@/lib/api/researchPlan';

/** Frozen inputs remain separate from the receipt's actual collection outcomes. */
export function SavedCollectionPlan({ plan }: { plan: ResearchPlan }) {
  const translation = plan.translation;
  return (
    <section className="space-y-3 border-y border-line py-4" aria-label="Saved collection plan">
      <h3 className="text-sm font-medium">Saved collection plan</h3>
      <p className="text-xs text-muted">
        The plan recorded when this version was collected. Recorded collection outcomes show what
        happened.
      </p>
      {!!plan.candidate_hypotheses?.length && (
        <section aria-label="Candidate hypotheses" className="space-y-2 text-xs">
          <h4 className="font-medium">Candidate hypotheses, not verified identities</h4>
          <ul>
            {plan.candidate_hypotheses.map((candidate) => (
              <li key={candidate.id} className="break-words" dir="auto">
                {candidate.label} ·{' '}
                {candidate.identifiers?.length
                  ? candidate.identifiers.join(' · ')
                  : 'No distinguishing identifiers supplied'}
              </li>
            ))}
          </ul>
        </section>
      )}
      {translation && (
        <section
          aria-label="Automatic query translation"
          className="space-y-3 border-y border-line py-3 text-xs"
        >
          <h4 className="font-medium">Automatic query translation</h4>
          <p>
            {translation.status === 'completed'
              ? 'Completed: generated phrases passed syntax and identifier checks only.'
              : translation.status === 'failed'
                ? 'Failed: no valid translation result was available; original terms were retained.'
                : 'Unavailable: no translation model was configured, so no translation call was made.'}
          </p>
          <p className="text-muted">
            Translation meaning has not been independently verified. Inspect the recorded phrases
            before relying on language coverage.
          </p>
          <dl className="grid gap-2 sm:grid-cols-2">
            <div>
              <dt className="text-muted">Model</dt>
              <dd className="break-words">{translation.model || 'Not recorded'}</dd>
            </div>
            <div>
              <dt className="text-muted">Translation policy</dt>
              <dd>{translation.policy_version}</dd>
            </div>
            <div>
              <dt className="text-muted">Requested languages</dt>
              <dd>{translation.languages.join(', ') || 'None recorded'}</dd>
            </div>
          </dl>
          <div>
            <h5 className="font-medium">Original search phrases</h5>
            {translation.original_terms.length ? (
              <ul>
                {translation.original_terms.map((term, index) => (
                  <li key={index} className="break-words" dir="auto">
                    {term}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No original phrases recorded.</p>
            )}
          </div>
          <div>
            <h5 className="font-medium">Recorded translated phrases</h5>
            {translation.variants.length ? (
              <ul className="space-y-2">
                {translation.variants.map((variant, index) => (
                  <li key={`${variant.language}:${index}`}>
                    <p className="text-muted">{variant.language}</p>
                    <ul>
                      {variant.terms.map((term, termIndex) => (
                        <li key={termIndex} className="break-words" dir="auto">
                          {term}
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No translated phrases recorded.</p>
            )}
          </div>
        </section>
      )}
      <p className="text-xs">
        Limits: {plan.request_limit} requests, {plan.seconds_limit} seconds, {plan.item_limit}{' '}
        items.
      </p>
      <ul className="divide-y divide-line text-xs">
        {plan.tasks.map((task, index) => (
          <li className="space-y-1 py-2" key={`${task.source_id}:${task.language ?? ''}:${index}`}>
            <p className="font-medium">
              {task.source_name} · {task.language ?? 'Language-independent'} ·{' '}
              {task.selected ? 'Selected' : 'Excluded'}
            </p>
            {task.purpose !== 'baseline' && (
              <p className="text-cyan">
                {task.purpose === 'challenge'
                  ? 'Conflicting evidence search'
                  : 'Identity candidate check'}
                {task.candidate_id
                  ? ` · Hypothesis: ${plan.candidate_hypotheses?.find((candidate) => candidate.id === task.candidate_id)?.label ?? task.candidate_id}`
                  : ''}
                {task.task_id ? ` · ${task.task_id}` : ''}
              </p>
            )}
            <p className="break-words text-muted" dir="auto">
              {task.terms.join(' · ') || 'No search terms recorded'}
            </p>
            {task.query_language && (
              <p className="text-muted">Query language: {task.query_language}</p>
            )}
            <p className="text-muted">
              {task.provenance === 'operator_supplied_variant'
                ? 'Operator-supplied language terms'
                : task.provenance === 'model_replanned_variant'
                  ? 'Model-replanned search terms'
                  : task.provenance === 'machine_translated_variant'
                    ? 'Machine-translated search terms, meaning unverified'
                    : task.provenance === 'original_terms'
                      ? 'Original terms'
                      : `Recorded provenance: ${task.provenance}`}{' '}
              · {task.temporal_scope}
            </p>
            {plan.area && (
              <p className="text-muted">
                {task.spatial_supported ? 'Area query supported' : 'Area query unsupported'}:{' '}
                {task.spatial_scope}
              </p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
