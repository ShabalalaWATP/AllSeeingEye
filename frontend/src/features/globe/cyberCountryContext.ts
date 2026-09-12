import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { Country } from '@/lib/api/geoSchemas';
import { hasCyberCountryContext } from '@/lib/cyber';

export interface CyberCountryContext {
  country: Country;
  events: LiveEvent[];
}

/** Country reference groups never change the geometry or precision of their evidence. */
export function cyberCountryGroups(
  events: readonly LiveEvent[],
  countries: Record<string, Country>,
): CyberCountryContext[] {
  const groups = new Map<string, CyberCountryContext>();
  for (const event of events) {
    if (!hasCyberCountryContext(event) || !event.country_iso) continue;
    const country = countries[event.country_iso];
    if (
      !country ||
      !Number.isFinite(country.centroid[0]) ||
      !Number.isFinite(country.centroid[1]) ||
      Math.abs(country.centroid[0]) > 180 ||
      Math.abs(country.centroid[1]) > 90
    )
      continue;
    const group = groups.get(country.iso2);
    if (group) group.events.push(event);
    else if (groups.size < 250) groups.set(country.iso2, { country, events: [event] });
  }
  return [...groups.values()].sort((a, b) => a.country.name.localeCompare(b.country.name));
}
