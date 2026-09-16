/** Pure filtering for the equipment catalogue: side, free text and counts per speciality. */
import type { EquipmentEntry, Side } from '@/lib/api/ukraine';

export type SideFilter = Side | 'both';

export function matchesQuery(entry: EquipmentEntry, query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (needle === '') return true;
  const haystack = [entry.name, entry.origin, entry.role, entry.description, entry.numbers ?? '']
    .join(' ')
    .toLowerCase();
  return needle.split(/\s+/).every((word) => haystack.includes(word));
}

export function filterEquipment(
  entries: readonly EquipmentEntry[],
  side: SideFilter,
  query: string,
): EquipmentEntry[] {
  return entries.filter(
    (entry) => (side === 'both' || entry.side === side) && matchesQuery(entry, query),
  );
}

export function countByGroup(entries: readonly EquipmentEntry[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const entry of entries) counts.set(entry.group, (counts.get(entry.group) ?? 0) + 1);
  return counts;
}
