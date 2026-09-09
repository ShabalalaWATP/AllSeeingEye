import type { LiveEvent } from './api/eventSchemas';

export type ConflictPrecision = 'all' | 'exact' | 'approximate';
export interface ConflictSourceChoice {
  value: string;
  label: string;
}

export function matchesConflictDisplay(
  event: LiveEvent,
  query: string,
  source: string,
  precision: ConflictPrecision,
): boolean {
  if (event.category !== 'conflict') return true;
  if (source !== 'all' && event.source_id !== source) return false;
  if (precision === 'exact' && (!event.point || event.geo_confidence !== 'exact')) return false;
  if (
    precision === 'approximate' &&
    (!event.point || !['city', 'admin1', 'country'].includes(event.geo_confidence))
  )
    return false;
  const words = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return true;
  const text = [event.title, event.title_en, event.summary, event.country_iso, event.subtype]
    .filter(Boolean)
    .join(' ')
    .toLocaleLowerCase();
  return words.every((word) => text.includes(word));
}

export function conflictSourceChoices(events: LiveEvent[]): ConflictSourceChoice[] {
  return [
    ...new Set(
      events.filter((event) => event.category === 'conflict').map((event) => event.source_id),
    ),
  ]
    .sort()
    .map((value) => ({ value, label: value.replaceAll('_', ' ') }));
}
