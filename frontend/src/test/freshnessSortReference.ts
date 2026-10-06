/** Frozen full-sort eviction oracle for the KAN-81 hint regression tests only. */
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { isSatellite, satellitePriority } from '@/lib/satellites';
import { isMilitaryAircraft, isMilitaryVessel } from '@/lib/traffic';
import { geographicOrder } from '@/stores/events.geography';

export const records = (events: readonly LiveEvent[]) =>
  Object.fromEntries(events.map((event) => [event.id, event]));

export function fullSortReference(
  input: Record<string, LiveEvent>,
  limit: number,
  selectedId?: string | null,
): Record<string, LiveEvent> {
  const events = Object.values(input);
  if (events.length <= limit) return input;
  const fair = geographicOrder(
    events.sort(
      (a, b) =>
        Date.parse(b.observed_at) - Date.parse(a.observed_at) ||
        Date.parse(b.published_at ?? b.observed_at) - Date.parse(a.published_at ?? a.observed_at) ||
        a.id.localeCompare(b.id),
    ),
  );
  const reserved = fair
    .filter((event) => event.category === 'maritime' && event.subtype === 'vessel_position')
    .sort((a, b) => Number(isMilitaryVessel(b)) - Number(isMilitaryVessel(a)))
    .slice(0, Math.min(1500, limit));
  reserved.push(
    ...fair
      .filter((event) => event.category === 'aviation')
      .sort((a, b) => Number(isMilitaryAircraft(b)) - Number(isMilitaryAircraft(a)))
      .slice(0, Math.min(1500, limit - reserved.length)),
  );
  reserved.push(
    ...fair
      .filter(isSatellite)
      .sort((a, b) => satellitePriority(b) - satellitePriority(a))
      .slice(0, Math.min(1000, limit - reserved.length)),
  );
  reserved.push(
    ...fair
      .filter(
        (event) =>
          event.category === 'disaster' &&
          event.subtype === 'thermal_detection' &&
          (event.source_id === 'firms' || event.source_id.startsWith('firms_')),
      )
      .slice(0, Math.min(500, limit - reserved.length)),
  );
  const ids = new Set(reserved.map((event) => event.id));
  const retained = [
    ...reserved,
    ...fair.filter((event) => !ids.has(event.id)).slice(0, limit - reserved.length),
  ];
  const selected = selectedId ? input[selectedId] : undefined;
  if (selected && retained.length && !retained.some((event) => event.id === selected.id))
    retained[retained.length - 1] = selected;
  return records(retained);
}
