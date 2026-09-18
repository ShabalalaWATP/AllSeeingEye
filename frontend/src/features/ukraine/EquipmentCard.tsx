import { useState } from 'react';

import { SIDE_LABELS, type EquipmentEntry, type UkraineReference } from '@/lib/api/ukraine';

import { formatDate, isStale } from './forceTree';
import { ReferenceImage } from './ReferenceImage';

const SIDE_ACCENT = { ru: 'border-t-chart-2', ua: 'border-t-chart-1' } as const;
const SIDE_CHIP = {
  ru: 'bg-chart-2/15 text-chart-2',
  ua: 'bg-chart-1/15 text-chart-1',
} as const;

/** One system: what it is, who fields it, what public reporting says about numbers. */
export function EquipmentCard({
  entry,
  reference,
  fetcher,
  showSide = false,
}: {
  entry: EquipmentEntry;
  reference: UkraineReference;
  fetcher?: ((path: string) => Promise<Blob>) | undefined;
  showSide?: boolean;
}) {
  const stale = isStale(entry.as_of, reference.retrieved_at);
  const [expanded, setExpanded] = useState(false);
  const long = entry.description.length > 220;
  return (
    <li
      className={`group flex flex-col overflow-hidden rounded-card border border-line border-t-2 bg-surface transition-colors hover:border-line/80 hover:bg-surface-2/40 motion-reduce:transition-none ${SIDE_ACCENT[entry.side]}`}
    >
      {entry.image_id ? (
        <ReferenceImage
          imageId={entry.image_id}
          meta={reference.images[entry.image_id]}
          alt={entry.name}
          fetcher={fetcher}
          cover
        />
      ) : null}
      <div className="flex flex-1 flex-col gap-2 p-3">
        <div className="flex items-start justify-between gap-2">
          <h5 className="text-sm leading-tight font-semibold text-text">{entry.name}</h5>
          <span className="flex shrink-0 flex-wrap justify-end gap-1">
            {showSide ? (
              <span
                className={`rounded-full px-2 py-0.5 font-mono text-[10px] ${SIDE_CHIP[entry.side]}`}
              >
                {SIDE_LABELS[entry.side]}
              </span>
            ) : null}
            <span className="rounded-full bg-surface-2 px-2 py-0.5 font-mono text-[10px] text-muted">
              {entry.origin}
            </span>
          </span>
        </div>
        <p className="text-xs font-medium text-cyan">{entry.role}</p>
        <p className={`text-xs leading-5 text-muted ${expanded ? '' : 'line-clamp-3'}`}>
          {entry.description}
        </p>
        {long ? (
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            aria-expanded={expanded}
            className="w-fit text-[11px] text-text underline-offset-2 hover:underline"
          >
            {expanded ? 'Show less' : 'Read more'}
          </button>
        ) : null}
        {entry.numbers ? (
          <p className="rounded border border-line/60 bg-ground px-2 py-1.5 text-xs leading-5 text-text">
            <span className="mr-1 font-mono text-[10px] tracking-wide text-muted uppercase">
              Reported
            </span>
            {entry.numbers}
          </p>
        ) : null}
        <div className="mt-auto flex flex-wrap items-center justify-between gap-x-3 gap-y-1 pt-1">
          <span className="flex flex-wrap gap-x-3">
            {entry.links.map((link) => (
              <a
                key={link.url}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] text-ember hover:underline"
              >
                {link.label}
              </a>
            ))}
          </span>
          <span className="font-mono text-[10px] text-muted">
            as of {formatDate(entry.as_of)}
            {stale ? ' (may be out of date)' : ''}
          </span>
        </div>
      </div>
    </li>
  );
}
