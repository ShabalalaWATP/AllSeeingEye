import { Link } from 'react-router';
import { HistoricalBaselineNote } from '@/components/reports/HistoricalBaselineNote';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { conflictReportLabel } from '@/lib/conflicts';
import { formatUtc } from '@/lib/format';
import { isHttpUrl } from '@/lib/urls';
import { eventResearchHref } from '@/lib/researchNavigation';
import { ConflictSourceProvenance } from './ConflictSourceProvenance';

function occurrence(event: LiveEvent): string {
  const value = event.attributes.occurrence_start ?? event.attributes.event_day;
  if (typeof value !== 'string' && typeof value !== 'number') return 'Unknown';
  const text = String(value);
  if (/^\d{8}$/.test(text)) return `${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6, 8)}`;
  return Number.isFinite(Date.parse(text)) ? formatUtc(text) : 'Unknown';
}

export function ConflictEvidenceRow({ event }: { event: LiveEvent }) {
  const precision = event.attributes.geo_precision;
  return (
    <article className="space-y-2 py-3">
      <HistoricalBaselineNote event={event} />
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] text-muted">
        <span className="text-cyan">{conflictReportLabel(event)}</span>
        <span>{event.source_id}</span>
        <span title={event.grade_rationale}>
          Source reliability {event.reliability} / Information credibility {event.credibility} /
          Grade {event.grade}
        </span>
      </div>
      <div className="text-sm font-medium">
        {isHttpUrl(event.url) ? (
          <a
            href={event.url}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-cyan hover:underline"
          >
            {event.title_en ?? event.title}
          </a>
        ) : (
          <span>{event.title_en ?? event.title}</span>
        )}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        <span>
          Occurred: {occurrence(event)}
          {event.attributes.date_precision != null &&
            ` · source date precision ${String(event.attributes.date_precision)}`}
          {typeof event.attributes.occurrence_end === 'string' &&
            event.attributes.occurrence_end !== event.attributes.occurrence_start &&
            ` to ${formatUtc(event.attributes.occurrence_end)}`}
        </span>
        <span>Published: {formatUtc(event.published_at)}</span>
        <span>
          Location: {event.geo_confidence}
          {typeof precision === 'string' || typeof precision === 'number'
            ? ` / source precision ${precision}`
            : ''}
        </span>
      </div>
      <ConflictSourceProvenance event={event} />
      <Link
        to={eventResearchHref(event)}
        aria-label={`Research this report: ${event.title}`}
        className="inline-flex min-h-9 items-center text-xs text-ember hover:underline"
      >
        Research this
      </Link>
    </article>
  );
}
