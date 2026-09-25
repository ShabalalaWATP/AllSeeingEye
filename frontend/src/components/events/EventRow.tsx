import { Link } from 'react-router';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { eventResearchHref } from '@/lib/researchNavigation';
import { formatUtc } from '@/lib/format';
import { isHttpUrl } from '@/lib/urls';
import { CATEGORY_STYLES } from '@/lib/categories';

/** One event as a list row: category chip, grade, time and the title as a link when safe. */
export function EventRow({ event }: { event: LiveEvent }) {
  const style = CATEGORY_STYLES[event.category];
  return (
    <li className="flex flex-wrap items-baseline gap-2 border-t border-line/60 py-2 text-sm">
      <span className="rounded px-1.5 font-mono text-2xs" style={{ color: style.css }}>
        {style.label}
      </span>
      <span className="font-mono text-2xs text-muted" title={event.grade_rationale}>
        {event.grade}
      </span>
      <span className="font-mono text-2xs text-muted">{formatUtc(event.published_at)}</span>
      {isHttpUrl(event.url) ? (
        <a
          href={event.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-text hover:underline"
        >
          {event.title_en ?? event.title}
        </a>
      ) : (
        <span className="text-text">{event.title_en ?? event.title}</span>
      )}
      <Link
        to={eventResearchHref(event)}
        aria-label={`Research this report: ${event.title}`}
        title="Review the question before starting research"
        className="inline-flex min-h-11 items-center text-xs text-ember hover:underline focus-visible:outline-2 focus-visible:outline-ember"
      >
        Research this
      </Link>
    </li>
  );
}
