import type { ResearchReceipt } from '@/lib/api/reportResearch';
import { formatUtc } from '@/lib/format';
import { SavedCollectionPlan } from '@/components/reports/SavedCollectionPlan';

export function ResearchCoverage({ receipt }: { receipt: ResearchReceipt | null | undefined }) {
  if (!receipt)
    return <p className="text-xs text-muted">Collection receipt not recorded for this version.</p>;
  const passes = receipt.passes ?? [];
  const observationTimes = receipt.time_basis === 'acquisition_or_publication';
  return (
    <details className="min-w-0 border-t border-line py-3 text-sm">
      <summary className="cursor-pointer py-1 font-medium focus-visible:outline-2 focus-visible:outline-ember">
        Collection coverage · {receipt.attempts.length} source outcome
        {receipt.attempts.length === 1 ? '' : 's'} · {receipt.collected_items} item
        {receipt.collected_items === 1 ? '' : 's'} collected
      </summary>
      <div className="mt-3 space-y-4 [overflow-wrap:anywhere]">
        <p className="text-xs text-muted">
          Saved collection activity, not proof of completeness.{' '}
          {observationTimes
            ? 'Dates filter acquisition time for observations and publication time for reporting, not retrieval time.'
            : 'Dates filter publication time, not necessarily event time.'}{' '}
          Empty or unavailable sources do not establish absence of events. Collected items may not
          all appear in the evidence annex.
        </p>
        <dl className="grid gap-3 text-xs sm:grid-cols-2">
          <div>
            <dt className="text-muted">Question</dt>
            <dd>{receipt.question}</dd>
          </div>
          <div>
            <dt className="text-muted">Mode / focus</dt>
            <dd>
              {receipt.mode} / {receipt.focus}
            </dd>
          </div>
          <div>
            <dt className="text-muted">Query languages</dt>
            <dd>{receipt.languages.join(', ') || 'Not recorded'}</dd>
          </div>
          <div>
            <dt className="text-muted">
              {observationTimes
                ? 'Acquisition/publication period (UTC)'
                : 'Publication period (UTC)'}
            </dt>
            <dd>
              {formatUtc(receipt.since)} to {formatUtc(receipt.until)}
            </dd>
          </div>
          <div>
            <dt className="text-muted">Query terms</dt>
            <dd>{receipt.terms.join(', ') || 'Not recorded'}</dd>
          </div>
          <div>
            <dt className="text-muted">Collection policy</dt>
            <dd>{receipt.policy_version}</dd>
          </div>
        </dl>
        {receipt.plan && !passes.some((pass) => pass.plan) && (
          <SavedCollectionPlan plan={receipt.plan} />
        )}
        <section aria-label="Latest source outcomes" className="space-y-2">
          <h3 className="font-medium">Latest source outcomes</h3>
          <p className="text-xs text-muted">
            The latest recorded outcome for each source. This count is not the total number of HTTP
            requests.
          </p>
          <CollectionAttempts attempts={receipt.attempts} />
        </section>
        {passes.length > 0 && (
          <section aria-label="Collection passes" className="space-y-4 border-t border-line pt-4">
            <h3 className="font-medium">Collection passes</h3>
            <p className="text-xs text-muted">
              These passes used one shared collection budget. A second pass does not reset the
              limits. An empty search does not establish absence of events.
            </p>
            {passes.map((pass, index) => (
              <section
                key={index}
                aria-label={`Collection pass ${index + 1}`}
                className="space-y-3 border-t border-line pt-4"
              >
                <h4 className="font-medium">Pass {index + 1}</h4>
                <div className="text-xs">
                  <p className="text-muted">Search terms for this pass</p>
                  <p className="break-words" dir="auto">
                    {pass.terms.join(' · ') || 'No search terms recorded'}
                  </p>
                </div>
                <CollectionAttempts attempts={pass.attempts} />
                {pass.plan ? (
                  <details>
                    <summary className="cursor-pointer py-2 text-xs font-medium">
                      Saved plan for pass {index + 1}
                    </summary>
                    <SavedCollectionPlan plan={pass.plan} />
                  </details>
                ) : (
                  <p className="text-xs text-muted">No plan recorded for this pass.</p>
                )}
              </section>
            ))}
          </section>
        )}
      </div>
    </details>
  );
}

function CollectionAttempts({ attempts }: { attempts: ResearchReceipt['attempts'] }) {
  if (!attempts.length) return <p className="text-muted">No collection attempts recorded.</p>;
  return (
    <ul className="divide-y divide-line">
      {attempts.map((attempt, index) => (
        <li key={index} className="py-3">
          <div className="flex flex-wrap justify-between gap-2">
            <span className="font-medium">{attempt.source_name}</span>
            <span className="font-mono text-xs capitalize">
              {attempt.status.replace(/_/g, ' ')} · {attempt.result_count} result
              {attempt.result_count === 1 ? '' : 's'}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted">
            {attempt.language ?? 'Language not recorded'} · {attempt.source_id}
          </p>
          <p className="mt-1 text-xs text-muted">{attempt.explanation}</p>
        </li>
      ))}
    </ul>
  );
}
