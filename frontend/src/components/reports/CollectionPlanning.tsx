import type { CollectionPlanningTrace } from '@/lib/api/collectionPlanning';
const statuses = {
  applied: 'Model proposals added to the collection plan',
  empty: 'The model returned no additional proposals',
  rejected: 'Model proposals were not accepted into the plan',
  unavailable: 'Automatic planning was unavailable',
  skipped: 'Automatic planning was skipped for this run',
};
export function CollectionPlanning({ value }: { value: CollectionPlanningTrace }) {
  return (
    <section
      aria-label="Automatic collection planning"
      className="space-y-3 border-y border-line py-4 text-xs"
    >
      <h3 className="font-medium text-text">Automatic collection planning</h3>
      <p className="text-cyan">{statuses[value.status]}</p>
      <p className="break-words" dir="auto">
        {value.reason}
      </p>
      <p className="text-muted">
        Proposals are planning suggestions, not findings. Added tasks may still be skipped or return
        no results; source task outcomes below record execution. Candidate identities remain
        unverified.
      </p>
      <dl className="grid gap-3 sm:grid-cols-2">
        <div>
          <dt className="text-muted">Initial planning model calls</dt>
          <dd>{value.call_count}</dd>
        </div>
        <div>
          <dt className="text-muted">Requested model</dt>
          <dd className="break-words">{value.requested_model || 'Not recorded'}</dd>
        </div>
        <div>
          <dt className="text-muted">Returned model</dt>
          <dd className="break-words">{value.returned_model || 'Not recorded'}</dd>
        </div>
        <div>
          <dt className="text-muted">Planning policy</dt>
          <dd>{value.policy_version}</dd>
        </div>
      </dl>
      {!!value.proposed_candidates.length && (
        <section aria-label="Model candidate proposals" className="space-y-2">
          <h4 className="font-medium">Model-proposed identity hypotheses</h4>
          <ul className="space-y-2">
            {value.proposed_candidates.map((candidate) => (
              <li key={candidate.id} className="break-words" dir="auto">
                <p>{candidate.label}</p>
                <p className="text-muted">
                  {candidate.identifiers?.length
                    ? candidate.identifiers.join(' / ')
                    : 'No distinguishing identifiers proposed'}
                </p>
                <p>
                  {value.accepted_candidate_ids.includes(candidate.id)
                    ? 'Added to plan, identity unverified'
                    : 'Not added to plan'}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}
      {!!value.proposed_tasks.length && (
        <section aria-label="Model search proposals" className="space-y-2">
          <h4 className="font-medium">Model-proposed searches</h4>
          <ul className="space-y-3">
            {value.proposed_tasks.map((task) => (
              <li key={task.id} className="space-y-1 break-words" dir="auto">
                <p>
                  {task.purpose === 'challenge'
                    ? 'Look for conflicting evidence'
                    : 'Distinguish an identity candidate'}{' '}
                  - {task.source_id}
                </p>
                <p>{task.terms.join(' / ')}</p>
                {task.candidate_id && (
                  <p className="text-muted">Candidate hypothesis: {task.candidate_id}</p>
                )}
                <p>
                  {value.accepted_task_ids.includes(`model:${task.id}`)
                    ? 'Added to plan; see recorded task outcome'
                    : 'Not added to plan'}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </section>
  );
}
