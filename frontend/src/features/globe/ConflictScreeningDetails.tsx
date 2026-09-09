import type { LiveEvent } from '@/lib/api/eventSchemas';
import { conflictReview } from '@/lib/conflictReview';

/** Separate relevance judgements from the provider's unchanged type, grade and location. */
export function ConflictScreeningDetails({ event }: { event: LiveEvent }) {
  const review = conflictReview(event);
  if (!review) return null;
  return (
    <section
      aria-label="Conflict relevance screening"
      className="mt-3 space-y-2 rounded-lg border border-line bg-surface-2/50 p-3 text-xs"
    >
      <span
        className={`inline-flex rounded border px-2 py-1 font-medium ${review.state === 'accepted' ? 'border-cyan-400/30 text-cyan-200' : 'border-amber-400/30 text-amber-200'}`}
      >
        {review.label}
      </span>
      <p className="text-muted">
        {review.assessed
          ? 'AI relevance screening of matched report text. This is not verification of the event, source reliability or location.'
          : 'Provider machine coding has not passed relevance screening. A generated title is not the original article headline, and matched source text may be unavailable.'}
      </p>
      {review.reason && <p>{review.reason}</p>}
      {review.quote && (
        <div>
          <p className="mb-1 text-muted">Text used for screening</p>
          <blockquote className="border-l-2 border-line pl-2">{review.quote}</blockquote>
        </div>
      )}
      {(review.model !== null || review.source !== null) && (
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 break-words">
          {review.source && (
            <>
              <dt className="text-muted">Matched source</dt>
              <dd>{review.source}</dd>
            </>
          )}
          {review.model && (
            <>
              <dt className="text-muted">Screening model</dt>
              <dd>{review.model}</dd>
            </>
          )}
        </dl>
      )}
    </section>
  );
}
