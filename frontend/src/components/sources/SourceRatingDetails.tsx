import type { SourceRating } from '@/lib/api/sourceContext';
import { formatUtc } from '@/lib/format';

/** Displays recorded editorial context without inferring a rating for an individual claim. */
export function SourceRatingDetails({
  rating,
  frozen = false,
}: {
  rating: SourceRating | null | undefined;
  frozen?: boolean;
}) {
  if (!rating)
    return <p className="text-xs text-muted">Source rating basis not recorded for this version.</p>;
  return (
    <details className="min-w-0 text-xs">
      <summary className="cursor-pointer py-2 font-medium focus-visible:outline-2 focus-visible:outline-ember">
        {frozen ? 'Saved source rating basis' : 'Source rating basis'} ·{' '}
        {rating.status === 'editorial'
          ? `Editorial ${rating.assessed_grade ?? 'unrecorded'}`
          : 'Unassessed'}
      </summary>
      <div className="space-y-3 py-2 text-muted [overflow-wrap:anywhere]">
        <p>
          {frozen ? 'Frozen with this report version.' : 'Current catalogue context.'} Editorial
          grades are not measured accuracy and do not establish the credibility of an individual
          claim.
        </p>
        <dl className="space-y-2">
          <div>
            <dt className="font-medium text-text">Basis</dt>
            <dd>{rating.basis}</dd>
          </div>
          <div>
            <dt className="font-medium text-text">Scope</dt>
            <dd>{rating.scope}</dd>
          </div>
          <div>
            <dt className="font-medium text-text">Provenance role</dt>
            <dd className="capitalize">{rating.provenance_role}</dd>
          </div>
          <div>
            <dt className="font-medium text-text">Publisher reliability assessed</dt>
            <dd>{rating.publisher_reliability_assessed ? 'Yes, within the stated scope' : 'No'}</dd>
          </div>
          <div>
            <dt className="font-medium text-text">Policy / review date</dt>
            <dd>
              {rating.policy_version} ·{' '}
              {rating.reviewed_at ? formatUtc(rating.reviewed_at) : 'Review date not recorded'}
            </dd>
          </div>
        </dl>
        <ul className="list-disc space-y-1 pl-4">
          {rating.limitations.map((text, index) => (
            <li key={index}>{text}</li>
          ))}
        </ul>
      </div>
    </details>
  );
}
