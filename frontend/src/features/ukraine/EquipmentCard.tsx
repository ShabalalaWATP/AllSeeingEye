import { SIDE_LABELS, type EquipmentEntry, type UkraineReference } from '@/lib/api/ukraine';

import { formatDate, isStale } from './forceTree';
import { ReferenceImage } from './ReferenceImage';

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
  return (
    <li className="flex flex-col gap-2 rounded-card border border-line bg-surface p-3">
      {entry.image_id ? (
        <ReferenceImage
          imageId={entry.image_id}
          meta={reference.images[entry.image_id]}
          alt={entry.name}
          fetcher={fetcher}
        />
      ) : null}
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h5 className="font-medium text-text">{entry.name}</h5>
        <span className="font-mono text-[10px] text-muted">
          {showSide ? `${SIDE_LABELS[entry.side]} · ` : ''}
          {entry.origin}
        </span>
      </div>
      <p className="text-xs text-muted">{entry.role}</p>
      <p className="text-sm text-muted">{entry.description}</p>
      {entry.numbers ? <p className="text-xs text-text">{entry.numbers}</p> : null}
      <div className="flex flex-wrap items-center gap-3">
        {entry.links.map((link) => (
          <a
            key={link.url}
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-ember hover:underline"
          >
            {link.label}
          </a>
        ))}
        <span className="font-mono text-[10px] text-muted">
          as of {formatDate(entry.as_of)}
          {stale ? ' (may be out of date)' : ''}
        </span>
      </div>
    </li>
  );
}
