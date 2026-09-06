import type { ReportChallenge } from '@/lib/api/reportChallenge';
import { Labels } from './EvidenceLinks';

export function ReportChallengeView({ challenge }: { challenge: ReportChallenge }) {
  return (
    <details className="min-w-0 border-t border-line py-3 text-sm">
      <summary className="cursor-pointer py-2 font-medium">
        Challenge to the judgements · {challenge.reviews.length} reviews
      </summary>
      <div className="mt-3 space-y-5 [overflow-wrap:anywhere]">
        <p className="text-xs text-muted">
          Automated challenges, not independent semantic proof. Initial searches and final reviews
          concern the statements shown below, which may differ after redrafting. An attempted search
          means a collection pass ran; individual providers may still have failed or exhausted their
          budget. Missing counterevidence does not confirm a claim.
        </p>
        <section aria-label="Final judgement reviews" className="space-y-3">
          <h2 className="font-semibold">Final judgement reviews</h2>
          {challenge.reviews.length === 0 && (
            <p className="text-xs text-muted">No final reviews recorded.</p>
          )}
          {challenge.reviews.map((review, index) => (
            <div key={index} className="space-y-2 border-l border-line pl-3">
              <p>
                <span className="font-mono text-xs text-muted">{review.judgement_id}</span>{' '}
                {review.statement}
              </p>
              <p className="text-xs text-muted">
                <span className="capitalize">{review.status}</span> · {review.explanation}
              </p>
              {review.advocacy && (
                <>
                  <p>
                    {review.advocacy.argument}
                    <Labels labels={review.advocacy.evidence} />
                  </p>
                  <p className="text-xs text-muted">{review.advocacy.rationale}</p>
                  <p className="text-xs text-muted">
                    Confidence before: {review.advocacy.confidence_before ?? 'Not recorded'} ·
                    after: {review.advocacy.confidence_after ?? 'Not recorded'}
                  </p>
                </>
              )}
            </div>
          ))}
        </section>
        <section aria-label="Initial challenge searches" className="space-y-3">
          <h2 className="font-semibold">Initial challenge searches</h2>
          {challenge.searches.length === 0 && (
            <p className="text-xs text-muted">No challenge search records saved.</p>
          )}
          {challenge.searches.map((search, index) => (
            <details key={index} className="border-l border-line pl-3 text-xs">
              <summary className="cursor-pointer py-2">
                {search.judgement_id} · {search.status.replace(/_/g, ' ')} ·{' '}
                {search.collected_items} collected
              </summary>
              <div className="space-y-2 py-2">
                <p className="text-sm">{search.statement}</p>
                <p className="text-muted">{search.explanation}</p>
                <p>Query terms: {search.terms.join(', ') || 'None recorded'}</p>
                {search.attempts.length === 0 && (
                  <p className="text-muted">No provider attempts recorded.</p>
                )}
                <ul className="divide-y divide-line">
                  {search.attempts.map((attempt, row) => (
                    <li key={row} className="space-y-1 py-2">
                      <p>
                        {attempt.source_name} · {attempt.status.replace(/_/g, ' ')} ·{' '}
                        {attempt.result_count} results
                      </p>
                      <p className="text-muted">
                        {attempt.language ?? 'Language not recorded'} · {attempt.explanation}
                      </p>
                    </li>
                  ))}
                </ul>
                <p className="font-mono text-[11px] text-muted">
                  Selected event IDs: {search.selected_event_ids.join(', ') || 'None recorded'}
                </p>
              </div>
            </details>
          ))}
        </section>
        <p className="text-xs text-muted">
          Redrafted after challenge: {challenge.redrafted ? 'Yes' : 'No'} · shared limits:{' '}
          {challenge.request_limit} requests, {challenge.seconds_limit} seconds
        </p>
        <p className="font-mono text-xs text-muted">
          Saved challenge method: {challenge.method_version}
        </p>
        <ul className="list-disc space-y-1 pl-4 text-xs text-muted">
          {challenge.limitations.map((text, index) => (
            <li key={index}>{text}</li>
          ))}
        </ul>
      </div>
    </details>
  );
}
