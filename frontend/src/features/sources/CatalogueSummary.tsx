import { FAMILIES, FAMILY_LABELS, type CatalogueEntry, type Family } from './catalogueEntries';
import { summariseFamilies, summariseGroups } from './catalogueEntries';
import { GROUPS, GROUP_LABELS, GROUP_TONE, type ConnectionGroup } from './connectionPresentation';

function Tile({
  label,
  count,
  tone,
  pressed,
  onSelect,
}: {
  label: string;
  count: number;
  tone: string;
  pressed: boolean;
  onSelect: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        aria-pressed={pressed}
        className={`flex w-full flex-col rounded-xl border p-4 text-left transition-colors hover:border-line focus-visible:outline-2 focus-visible:outline-ember ${pressed ? 'border-ember bg-surface-2' : 'border-line/70 bg-surface/60'}`}
      >
        <span className="text-[11px] text-muted">{label}</span>
        <span className={`mt-1 text-2xl font-semibold tracking-tight ${tone}`}>{count}</span>
      </button>
    </li>
  );
}

/** Totals by state and by family; each tile filters the catalogue below. */
export function CatalogueSummary({
  entries,
  connection,
  family,
  onConnection,
  onFamily,
}: {
  entries: readonly CatalogueEntry[];
  connection: string;
  family: string;
  onConnection: (group: ConnectionGroup) => void;
  onFamily: (family: Family) => void;
}) {
  const groups = summariseGroups(entries);
  const families = summariseFamilies(entries);
  return (
    <section aria-label="Catalogue summary" className="space-y-4">
      <p className="text-sm text-muted">
        <span className="font-mono text-text">{entries.length}</span> sources, services and datasets
        on this server.
      </p>
      <div className="space-y-2">
        <h2 className="text-xs font-medium tracking-wide text-muted uppercase">By state</h2>
        <ul aria-label="Totals by state" className="grid grid-cols-2 gap-3 md:grid-cols-6">
          {GROUPS.map((group) => (
            <Tile
              key={group}
              label={GROUP_LABELS[group]}
              count={groups[group]}
              tone={GROUP_TONE[group]}
              pressed={connection === group}
              onSelect={() => onConnection(group)}
            />
          ))}
        </ul>
      </div>
      <div className="space-y-2">
        <h2 className="text-xs font-medium tracking-wide text-muted uppercase">By family</h2>
        <ul aria-label="Totals by family" className="grid grid-cols-2 gap-3 md:grid-cols-6">
          {FAMILIES.map((value) => (
            <Tile
              key={value}
              label={FAMILY_LABELS[value]}
              count={families[value]}
              tone="text-text"
              pressed={family === value}
              onSelect={() => onFamily(value)}
            />
          ))}
        </ul>
      </div>
    </section>
  );
}
