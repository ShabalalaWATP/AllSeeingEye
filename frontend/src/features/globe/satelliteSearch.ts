import type { LiveEvent } from '@/lib/api/eventSchemas';

export const SATELLITE_QUERY_LIMIT = 200;
export const SATELLITE_PAGE_SIZE = 25;
const searchText = new WeakMap<LiveEvent, string>();

function catalogueValue(value: unknown): string {
  return typeof value === 'string' || typeof value === 'number' ? String(value) : '';
}

/** Search only supplied catalogue metadata. Weak keys release replaced positions. */
export function matchesSatelliteSearch(event: LiveEvent, terms: readonly string[]): boolean {
  if (!terms.length) return true;
  let text = searchText.get(event);
  if (text === undefined) {
    text = [event.title, event.attributes.norad_id, event.attributes.object_id]
      .map(catalogueValue)
      .join(' ')
      .toLocaleLowerCase('en-GB');
    searchText.set(event, text);
  }
  return terms.every((term) => text.includes(term));
}

export function satelliteIdentifiers(event: LiveEvent): string {
  return [
    catalogueValue(event.attributes.norad_id)
      ? `NORAD ${catalogueValue(event.attributes.norad_id)}`
      : '',
    catalogueValue(event.attributes.object_id),
  ]
    .filter(Boolean)
    .join(' · ');
}
