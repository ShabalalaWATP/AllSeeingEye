import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { Country } from '@/lib/api/geoSchemas';
import { isNetworkSource } from './networkSources';

export interface NetworkCountryGroup {
  country: Country;
  events: LiveEvent[];
}

/** Only provider-attributed countries can produce a map reference. */
export function networkCountryGroups(
  events: readonly LiveEvent[],
  countries: Record<string, Country>,
): NetworkCountryGroup[] {
  const grouped = new Map<string, NetworkCountryGroup>();
  for (const event of events) {
    if (
      !isNetworkSource(event.source_id) ||
      event.geo_confidence !== 'country' ||
      !event.country_iso
    )
      continue;
    const country = countries[event.country_iso];
    if (
      !country ||
      !Number.isFinite(country.centroid[0]) ||
      !Number.isFinite(country.centroid[1]) ||
      Math.abs(country.centroid[0]) > 180 ||
      Math.abs(country.centroid[1]) > 90
    )
      continue;
    const group = grouped.get(country.iso2);
    if (group) group.events.push(event);
    else grouped.set(country.iso2, { country, events: [event] });
  }
  return [...grouped.values()].sort((a, b) => a.country.name.localeCompare(b.country.name));
}
