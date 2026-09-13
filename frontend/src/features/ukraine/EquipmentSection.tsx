import { useMemo, useState } from 'react';

import { Table, Td, Th } from '@/components/ui/Table';
import {
  SIDE_LABELS,
  type EquipmentEntry,
  type Side,
  type UkraineReference,
} from '@/lib/api/ukraine';

import { ReferenceImage } from './ReferenceImage';

type Fetcher = ((path: string) => Promise<Blob>) | undefined;
const SIDES: readonly Side[] = ['ru', 'ua'];

function EquipmentCard({
  entry,
  reference,
  fetcher,
}: {
  entry: EquipmentEntry;
  reference: UkraineReference;
  fetcher: Fetcher;
}) {
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
        <span className="font-mono text-[10px] text-muted">{entry.origin}</span>
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
        <span className="font-mono text-[10px] text-muted">as of {entry.as_of}</span>
      </div>
    </li>
  );
}

function CompareTable({ entries, label }: { entries: readonly EquipmentEntry[]; label: string }) {
  return (
    <Table caption={label}>
      <thead>
        <tr>
          <Th>Side</Th>
          <Th>System</Th>
          <Th>Origin</Th>
          <Th>Role</Th>
          <Th>Numbers (reported)</Th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry) => (
          <tr key={entry.id}>
            <Td>{SIDE_LABELS[entry.side]}</Td>
            <Td>{entry.name}</Td>
            <Td>{entry.origin}</Td>
            <Td>{entry.role}</Td>
            <Td>{entry.numbers ?? 'Not stated'}</Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

/** Headings inside headings: speciality, then sub-heading, then a card column per side. */
export function EquipmentSection({
  reference,
  fetcher,
}: {
  reference: UkraineReference;
  fetcher?: Fetcher;
}) {
  const [group, setGroup] = useState<string>(reference.specialities[0]?.key ?? 'drones');
  const [compare, setCompare] = useState(false);
  const speciality = reference.specialities.find((item) => item.key === group);
  const entries = useMemo(
    () => reference.equipment.filter((entry) => entry.group === group),
    [reference.equipment, group],
  );
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
        <button
          type="button"
          aria-pressed={compare}
          onClick={() => setCompare((value) => !value)}
          className="min-h-9 rounded border border-line px-3 text-xs text-muted aria-pressed:border-cyan aria-pressed:text-cyan"
        >
          Compare as a table
        </button>
      </div>
      <div role="group" aria-label="Speciality" className="flex flex-wrap gap-1">
        {reference.specialities.map((item) => (
          <button
            key={item.key}
            type="button"
            aria-pressed={group === item.key}
            onClick={() => setGroup(item.key)}
            className="min-h-10 rounded border border-line px-3 text-xs text-muted aria-pressed:border-cyan aria-pressed:bg-cyan/10 aria-pressed:text-cyan"
          >
            {item.label} ({reference.equipment.filter((entry) => entry.group === item.key).length})
          </button>
        ))}
      </div>
      {speciality ? (
        <div className="flex flex-col gap-4">
          <h3 className="text-sm font-semibold text-text">{speciality.label}</h3>
          {compare ? (
            <CompareTable entries={entries} label={`${speciality.label}: systems side by side`} />
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
                  <div className="grid gap-3 lg:grid-cols-2">
                    {SIDES.map((side) => {
                      const column = entries.filter(
                        (entry) => entry.subgroup === key && entry.side === side,
                      );
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
                </section>
              ))
          )}
        </div>
      ) : null}
    </section>
  );
}
