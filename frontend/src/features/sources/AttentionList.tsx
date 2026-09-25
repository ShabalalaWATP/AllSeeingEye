import { ConnectionBadge } from './ConnectionBadge';
import {
  FAMILY_LABELS,
  attentionEntries,
  attentionReason,
  type CatalogueEntry,
} from './catalogueEntries';

const LIMIT = 15;

/** Only actionable entries: upstream refusals, paused feeds and missing required settings. */
export function AttentionList({ entries }: { entries: readonly CatalogueEntry[] }) {
  const items = attentionEntries(entries);
  if (!items.length) return null;
  return (
    <section
      aria-label="Needs attention"
      className="rounded-xl border border-amber/40 bg-amber/5 p-4 sm:p-5"
    >
      <h2 className="text-sm font-semibold">Needs attention</h2>
      <p className="mt-1 text-xs leading-5 text-muted">
        Items an operator can act on: an upstream that refuses this server or account, a feed paused
        after repeated failures, or a required key or setup step. Optional settings, on-demand tools
        and short retries are not listed.
      </p>
      <ul className="mt-3 divide-y divide-line/60">
        {items.slice(0, LIMIT).map((entry) => (
          <li key={entry.id} className="flex flex-wrap items-center gap-3 py-2 text-sm">
            <ConnectionBadge state={entry.state} />
            <span className="font-medium">{entry.name}</span>
            <span className="text-[11px] text-muted">{FAMILY_LABELS[entry.family]}</span>
            <span className="min-w-0 basis-full text-xs leading-5 text-muted">
              {attentionReason(entry)}
            </span>
            {entry.requirement?.setting && entry.state !== 'blocked_upstream' && (
              <span className="font-mono text-2xs text-muted">{entry.requirement.setting}</span>
            )}
          </li>
        ))}
      </ul>
      {items.length > LIMIT && (
        <p className="mt-2 text-xs text-muted">
          {items.length - LIMIT} more in the catalogue below.
        </p>
      )}
    </section>
  );
}
