import { Fragment } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { eventFacts } from './eventFacts';

export function SelectedEventFacts({ event }: { event: LiveEvent }) {
  const group = eventFacts(event);
  if (!group) return null;
  return (
    <section aria-label={group.title} className="mt-4 border-y border-line py-3">
      <h3 className="text-xs font-semibold tracking-wide text-text">{group.title}</h3>
      <dl className="mt-2 grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-x-3 gap-y-2 text-xs">
        {group.facts.map(({ label, value }) => (
          <Fragment key={label}>
            <dt className="text-muted">{label}</dt>
            <dd className="break-words text-right font-mono text-text">{value}</dd>
          </Fragment>
        ))}
      </dl>
      <p className="mt-3 text-xs leading-relaxed text-muted">{group.note}</p>
    </section>
  );
}
