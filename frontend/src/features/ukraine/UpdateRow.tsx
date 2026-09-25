import { Link } from 'react-router';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { LENS_LABELS, type UkraineUpdate } from '@/lib/api/ukraine';
import { formatUtc } from '@/lib/format';
import { eventResearchHref } from '@/lib/researchNavigation';
import { isHttpUrl } from '@/lib/urls';

function sourceLabel(event: LiveEvent): string {
  return event.source_id.replace(/_/g, ' ');
}

/** One retained item: source, grade, time, lens chips, a safe title link and a research link. */
export function UpdateRow({ update }: { update: UkraineUpdate }) {
  const { event } = update;
  const title = event.title_en ?? event.title;
  const state = event.tags.includes('state_controlled');
  return (
    <li className="flex flex-col gap-1 border-t border-line/60 py-2 text-sm">
      <div className="flex flex-wrap items-baseline gap-2">
        <span className="font-mono text-2xs uppercase text-muted">{sourceLabel(event)}</span>
        {state ? (
          <span className="rounded border border-amber-300/60 px-1 font-mono text-2xs text-amber-300">
            state media
          </span>
        ) : null}
        <span className="font-mono text-2xs text-muted" title={event.grade_rationale}>
          {event.grade}
        </span>
        <span className="font-mono text-2xs text-muted">{formatUtc(event.published_at)}</span>
        {update.lenses.map((lens) => (
          <span key={lens} className="rounded bg-surface-2 px-1 font-mono text-2xs text-muted">
            {LENS_LABELS[lens]}
          </span>
        ))}
      </div>
      {isHttpUrl(event.url) ? (
        <a
          href={event.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-text hover:underline"
        >
          {title}
        </a>
      ) : (
        <span className="text-text">{title}</span>
      )}
      <div className="flex flex-wrap items-baseline gap-3">
        {event.summary ? <p className="text-xs text-muted">{event.summary}</p> : null}
        <Link
          to={eventResearchHref(event)}
          aria-label={`Research this report: ${event.title}`}
          className="text-xs text-ember hover:underline"
        >
          Research this
        </Link>
      </div>
    </li>
  );
}
