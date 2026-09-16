import { useMemo, useState } from 'react';

import {
  SIDE_LABELS,
  type EquipmentEntry,
  type Side,
  type UkraineReference,
} from '@/lib/api/ukraine';

import { EquipmentCard } from './EquipmentCard';
import { EquipmentCompareTable } from './EquipmentCompareTable';
import { countByGroup, filterEquipment, type SideFilter } from './equipmentFilter';

type Fetcher = ((path: string) => Promise<Blob>) | undefined;

const SIDE_FILTERS: readonly (readonly [SideFilter, string])[] = [
  ['both', 'Both sides'],
  ['ru', SIDE_LABELS.ru],
  ['ua', SIDE_LABELS.ua],
];

function SubgroupColumns({
  entries,
  sides,
  reference,
  fetcher,
}: {
  entries: readonly EquipmentEntry[];
  sides: readonly Side[];
  reference: UkraineReference;
  fetcher: Fetcher;
}) {
  return (
    <div className={sides.length > 1 ? 'grid gap-3 lg:grid-cols-2' : 'flex flex-col gap-3'}>
      {sides.map((side) => {
        const column = entries.filter((entry) => entry.side === side);
        return (
          <div key={side} className="flex flex-col gap-2">
            <span className="font-mono text-[10px] uppercase tracking-wide text-muted">
              {SIDE_LABELS[side]}
            </span>
            {column.length === 0 ? (
              <p className="text-xs text-muted">No entry written yet.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {column.map((entry) => (
                  <EquipmentCard
                    key={entry.id}
                    entry={entry}
                    reference={reference}
                    fetcher={fetcher}
                  />
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}

/** Speciality, then sub-heading, then a card column per side, with a side filter and a search. */
export function EquipmentSection({
  reference,
  fetcher,
}: {
  reference: UkraineReference;
  fetcher?: Fetcher;
}) {
  const [group, setGroup] = useState<string>(reference.specialities[0]?.key ?? 'drones');
  const [compare, setCompare] = useState(false);
  const [side, setSide] = useState<SideFilter>('both');
  const [query, setQuery] = useState('');
  const matching = useMemo(
    () => filterEquipment(reference.equipment, side, query),
    [reference.equipment, side, query],
  );
  const counts = useMemo(() => countByGroup(matching), [matching]);
  const speciality = reference.specialities.find((item) => item.key === group);
  const entries = useMemo(
    () => matching.filter((entry) => entry.group === group),
    [matching, group],
  );
  const sides: readonly Side[] = side === 'both' ? ['ru', 'ua'] : [side];
  return (
    <section
      id="equipment"
      aria-labelledby="ukraine-equipment-heading"
      className="flex flex-col gap-3"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="ukraine-equipment-heading" className="text-base font-semibold">
          Equipment by speciality
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          <div role="group" aria-label="Side" className="flex flex-wrap gap-1">
            {SIDE_FILTERS.map(([key, label]) => (
              <button
                key={key}
                type="button"
                aria-pressed={side === key}
                onClick={() => setSide(key)}
                className="min-h-10 rounded border border-line px-3 text-xs text-muted aria-pressed:border-cyan aria-pressed:bg-cyan/10 aria-pressed:text-cyan"
              >
                {label}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-2 text-xs text-muted">
            <span>Search</span>
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Name, origin or role"
              className="min-h-10 w-44 rounded border border-line bg-surface px-2 text-xs text-text"
            />
          </label>
          <button
            type="button"
            aria-pressed={compare}
            onClick={() => setCompare((value) => !value)}
            className="min-h-10 rounded border border-line px-3 text-xs text-muted aria-pressed:border-cyan aria-pressed:text-cyan"
          >
            Compare as a table
          </button>
        </div>
      </div>
      <p className="max-w-3xl text-xs text-muted">
        {matching.length} of {reference.equipment.length} entries match. Each says what the system
        is for and what public reporting claims about it; numbers name whose estimate they are and
        when it was made.
      </p>
      <div role="group" aria-label="Speciality" className="flex flex-wrap gap-1">
        {reference.specialities.map((item) => (
          <button
            key={item.key}
            type="button"
            aria-pressed={group === item.key}
            onClick={() => setGroup(item.key)}
            className="min-h-10 rounded border border-line px-3 text-xs text-muted aria-pressed:border-cyan aria-pressed:bg-cyan/10 aria-pressed:text-cyan"
          >
            {item.label} ({counts.get(item.key) ?? 0})
          </button>
        ))}
      </div>
      {speciality ? (
        <div className="flex flex-col gap-4">
          <h3 className="text-sm font-semibold text-text">{speciality.label}</h3>
          {entries.length === 0 ? (
            <p className="text-xs text-muted">
              No entry in this speciality matches the current side and search.
            </p>
          ) : compare ? (
            <EquipmentCompareTable
              entries={entries}
              label={`${speciality.label}: systems side by side`}
            />
          ) : (
            Object.entries(speciality.subgroups)
              .filter(([key]) => entries.some((entry) => entry.subgroup === key))
              .map(([key, label]) => (
                <section
                  key={key}
                  aria-label={`${speciality.label}: ${label}`}
                  className="flex flex-col gap-2"
                >
                  <h4 className="text-sm font-medium text-muted">{label}</h4>
                  <SubgroupColumns
                    entries={entries.filter((entry) => entry.subgroup === key)}
                    sides={sides}
                    reference={reference}
                    fetcher={fetcher}
                  />
                </section>
              ))
          )}
        </div>
      ) : null}
    </section>
  );
}
