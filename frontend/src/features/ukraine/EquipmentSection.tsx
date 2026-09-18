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
const SIDE_DOT = { ru: 'bg-chart-2', ua: 'bg-chart-1' } as const;

const SEGMENT =
  'min-h-9 rounded-full px-3 text-xs text-muted transition-colors aria-pressed:bg-surface aria-pressed:text-text aria-pressed:shadow-sm hover:text-text motion-reduce:transition-none';

function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: readonly (readonly [T, string])[];
  value: T;
  onChange: (next: T) => void;
}) {
  return (
    <div role="group" aria-label={label} className="flex gap-0.5 rounded-full bg-surface-2 p-0.5">
      {options.map(([key, text]) => (
        <button
          key={key}
          type="button"
          aria-pressed={value === key}
          onClick={() => onChange(key)}
          className={SEGMENT}
        >
          {text}
        </button>
      ))}
    </div>
  );
}

/** A side's cards in a panel that scrolls on its own, so a long subgroup never runs the page. */
function SideColumn({
  side,
  entries,
  reference,
  fetcher,
}: {
  side: Side;
  entries: readonly EquipmentEntry[];
  reference: UkraineReference;
  fetcher: Fetcher;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <div className="flex items-center gap-2 font-mono text-[10px] tracking-wide text-muted uppercase">
        <span aria-hidden="true" className={`size-2 rounded-full ${SIDE_DOT[side]}`} />
        {SIDE_LABELS[side]}
        <span className="text-text">{entries.length}</span>
      </div>
      {entries.length === 0 ? (
        <p className="rounded-card border border-dashed border-line p-4 text-xs text-muted">
          No entry written yet.
        </p>
      ) : (
        <ul className="grid max-h-[34rem] grid-cols-[repeat(auto-fill,minmax(13rem,1fr))] content-start gap-3 overflow-y-auto pr-1 pb-1">
          {entries.map((entry) => (
            <EquipmentCard key={entry.id} entry={entry} reference={reference} fetcher={fetcher} />
          ))}
        </ul>
      )}
    </div>
  );
}

/** Speciality tabs, then a collapsible section per sub-heading with a scrolling column per side. */
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
  const [closed, setClosed] = useState<ReadonlySet<string>>(new Set());
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
  const subgroups = speciality
    ? Object.entries(speciality.subgroups).filter(([key]) =>
        entries.some((entry) => entry.subgroup === key),
      )
    : [];
  const allClosed =
    subgroups.length > 0 && subgroups.every(([key]) => closed.has(`${group}:${key}`));
  const setOpen = (key: string, open: boolean) =>
    setClosed((current) => {
      const next = new Set(current);
      if (open) next.delete(key);
      else next.add(key);
      return next;
    });
  return (
    <section
      id="equipment"
      aria-labelledby="ukraine-equipment-heading"
      className="flex flex-col gap-4 rounded-card border border-line bg-ground/60 p-4 sm:p-5"
    >
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="mb-1 font-mono text-[10px] tracking-[0.22em] text-cyan uppercase">
            Reference
          </p>
          <h2 id="ukraine-equipment-heading" className="text-lg font-semibold tracking-tight">
            Equipment catalogue
          </h2>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-muted">
            What each system is for and what public reporting claims about it. Numbers name whose
            estimate they are and when it was made.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Segmented label="Side" options={SIDE_FILTERS} value={side} onChange={setSide} />
          <label className="flex items-center gap-2 text-xs text-muted">
            <span className="sr-only">Search</span>
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search name, origin or role"
              className="min-h-9 w-52 rounded-full border border-line bg-surface px-3 text-xs text-text placeholder:text-muted focus:border-cyan focus:outline-none"
            />
          </label>
          <button
            type="button"
            aria-pressed={compare}
            onClick={() => setCompare((value) => !value)}
            className="min-h-9 rounded-full border border-line px-3 text-xs text-muted transition-colors aria-pressed:border-cyan aria-pressed:bg-cyan/10 aria-pressed:text-cyan hover:text-text motion-reduce:transition-none"
          >
            Compare as a table
          </button>
        </div>
      </div>

      <div
        role="group"
        aria-label="Speciality"
        className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-1 [scrollbar-width:thin]"
      >
        {reference.specialities.map((item) => (
          <button
            key={item.key}
            type="button"
            aria-pressed={group === item.key}
            onClick={() => setGroup(item.key)}
            className="flex min-h-9 shrink-0 items-center gap-2 rounded-full border border-line px-3 text-xs whitespace-nowrap text-muted transition-colors aria-pressed:border-cyan aria-pressed:bg-cyan/10 aria-pressed:text-cyan hover:border-line/80 hover:text-text motion-reduce:transition-none"
          >
            {item.label}{' '}
            <span className="rounded-full bg-surface-2 px-1.5 font-mono text-[10px] text-muted">
              ({counts.get(item.key) ?? 0})
            </span>
          </button>
        ))}
      </div>

      {speciality ? (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line pb-2">
            <h3 className="text-sm font-semibold text-text">
              {speciality.label}{' '}
              <span className="font-mono text-[11px] font-normal text-muted">
                {entries.length} of {matching.length} matching entries
              </span>
            </h3>
            {!compare && subgroups.length > 1 ? (
              <button
                type="button"
                onClick={() =>
                  setClosed(
                    allClosed ? new Set() : new Set(subgroups.map(([key]) => `${group}:${key}`)),
                  )
                }
                className="min-h-9 text-xs text-muted hover:text-text"
              >
                {allClosed ? 'Expand all' : 'Collapse all'}
              </button>
            ) : null}
          </div>
          {entries.length === 0 ? (
            <p className="rounded-card border border-dashed border-line p-6 text-center text-xs text-muted">
              No entry in this speciality matches the current side and search.
            </p>
          ) : compare ? (
            <EquipmentCompareTable
              entries={entries}
              label={`${speciality.label}: systems side by side`}
            />
          ) : (
            subgroups.map(([key, label]) => {
              const id = `${group}:${key}`;
              const rows = entries.filter((entry) => entry.subgroup === key);
              return (
                <section key={key} aria-label={`${speciality.label}: ${label}`}>
                  <details
                    open={!closed.has(id)}
                    onToggle={(event) => setOpen(id, event.currentTarget.open)}
                    className="group/sub rounded-card border border-line bg-surface/60"
                  >
                    <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 px-4 text-sm font-medium text-text select-none [&::-webkit-details-marker]:hidden">
                      <span className="flex items-center gap-2">
                        <span
                          aria-hidden="true"
                          className="text-muted transition-transform group-open/sub:rotate-90 motion-reduce:transition-none"
                        >
                          ▸
                        </span>
                        {label}
                      </span>
                      <span className="font-mono text-[10px] text-muted">
                        {rows.length} {rows.length === 1 ? 'system' : 'systems'}
                      </span>
                    </summary>
                    <div
                      className={`border-t border-line px-4 py-3 ${
                        sides.length > 1 ? 'grid gap-4 lg:grid-cols-2' : 'flex flex-col gap-3'
                      }`}
                    >
                      {sides.map((item) => (
                        <SideColumn
                          key={item}
                          side={item}
                          entries={rows.filter((entry) => entry.side === item)}
                          reference={reference}
                          fetcher={fetcher}
                        />
                      ))}
                    </div>
                  </details>
                </section>
              );
            })
          )}
        </div>
      ) : null}
    </section>
  );
}
