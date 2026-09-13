import { useMemo, useState } from 'react';
import { Link } from 'react-router';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import {
  GROUP_LABELS,
  LENS_LABELS,
  type Lens,
  type UkraineUpdate,
  type UpdateGroup,
} from '@/lib/api/ukraine';
import { formatUtc } from '@/lib/format';
import { eventResearchHref } from '@/lib/researchNavigation';
import { isHttpUrl } from '@/lib/urls';

const GROUPS: readonly UpdateGroup[] = ['assessments', 'ukrainian', 'russian', 'international'];
const LENSES: readonly Lens[] = ['equipment', 'workforce', 'casualties', 'strikes', 'diplomacy'];

function sourceLabel(event: LiveEvent): string {
  return event.source_id.replace(/_/g, ' ');
}

function UpdateRow({ update }: { update: UkraineUpdate }) {
  const { event } = update;
  const title = event.title_en ?? event.title;
  const state = event.tags.includes('state_controlled');
  return (
    <li className="flex flex-col gap-1 border-t border-line/60 py-2 text-sm">
      <div className="flex flex-wrap items-baseline gap-2">
        <span className="font-mono text-[10px] uppercase text-muted">{sourceLabel(event)}</span>
        {state ? (
          <span className="rounded border border-amber-300/60 px-1 font-mono text-[10px] text-amber-300">
            state media
          </span>
        ) : null}
        <span className="font-mono text-[10px] text-muted" title={event.grade_rationale}>
          {event.grade}
        </span>
        <span className="font-mono text-[10px] text-muted">{formatUtc(event.published_at)}</span>
        {update.lenses.map((lens) => (
          <span key={lens} className="rounded bg-surface-2 px-1 font-mono text-[10px] text-muted">
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

/** Reporting grouped by who says it, with lens chips that narrow every group the same way. */
export function UpdatesTabs({ updates }: { updates: readonly UkraineUpdate[] }) {
  const [group, setGroup] = useState<UpdateGroup>('assessments');
  const [lens, setLens] = useState<Lens | null>(null);
  const counts = useMemo(() => {
    const perGroup = new Map<UpdateGroup, number>();
    for (const update of updates) {
      if (lens && !update.lenses.includes(lens)) continue;
      perGroup.set(update.group, (perGroup.get(update.group) ?? 0) + 1);
    }
    return perGroup;
  }, [updates, lens]);
  const visible = updates.filter(
    (update) => update.group === group && (lens === null || update.lenses.includes(lens)),
  );
  return (
    <section id="updates" aria-labelledby="ukraine-updates-heading" className="flex flex-col gap-3">
      <h2 id="ukraine-updates-heading" className="text-base font-semibold">
        Latest updates
      </h2>
      <div role="group" aria-label="Reporting group" className="flex flex-wrap gap-1">
        {GROUPS.map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={group === value}
            onClick={() => setGroup(value)}
            className="min-h-10 rounded border border-line px-3 text-xs text-muted aria-pressed:border-cyan aria-pressed:bg-cyan/10 aria-pressed:text-cyan"
          >
            {GROUP_LABELS[value]} ({counts.get(value) ?? 0})
          </button>
        ))}
      </div>
      <div role="group" aria-label="Lens" className="flex flex-wrap gap-1">
        <button
          type="button"
          aria-pressed={lens === null}
          onClick={() => setLens(null)}
          className="min-h-9 rounded-full border border-line px-3 text-xs text-muted aria-pressed:border-ember aria-pressed:text-ember"
        >
          All
        </button>
        {LENSES.map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={lens === value}
            onClick={() => setLens(lens === value ? null : value)}
            className="min-h-9 rounded-full border border-line px-3 text-xs text-muted aria-pressed:border-ember aria-pressed:text-ember"
          >
            {LENS_LABELS[value]}
          </button>
        ))}
      </div>
      {visible.length === 0 ? (
        <p className="text-sm text-muted">Nothing retained for this group in the window.</p>
      ) : (
        <ul aria-label={GROUP_LABELS[group]}>
          {visible.map((update) => (
            <UpdateRow key={update.event.id} update={update} />
          ))}
        </ul>
      )}
    </section>
  );
}
