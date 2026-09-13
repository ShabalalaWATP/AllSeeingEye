import { useCallback, useMemo, useState } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { Country } from '@/lib/api/geoSchemas';
import { isNewsCategory } from './newsFilters';

export interface NewsCountryContext {
  country: Country;
  events: LiveEvent[];
}

/** Source-supplied country references, never headline guesses or publisher headquarters. */
export function newsCountryGroups(
  events: readonly LiveEvent[],
  countries: Record<string, Country>,
) {
  const groups = new Map<string, NewsCountryContext>();
  for (const event of events) {
    if (!isNewsCategory(event.category) || event.geo_confidence !== 'country' || !event.country_iso)
      continue;
    const country = countries[event.country_iso];
    if (
      !country ||
      !country.centroid.every(Number.isFinite) ||
      Math.abs(country.centroid[0]) > 180 ||
      Math.abs(country.centroid[1]) > 90
    )
      continue;
    const group = groups.get(country.iso2) ?? { country, events: [] };
    group.events.push(event);
    groups.set(country.iso2, group);
  }
  return [...groups.values()].slice(0, 250);
}

export function useNewsCountryContext(
  events: readonly LiveEvent[],
  countries: Record<string, Country>,
  scope: string,
) {
  const groups = useMemo(() => newsCountryGroups(events, countries), [events, countries]);
  const [selection, setSelection] = useState<{ scope: string; iso: string } | null>(null);
  const selected =
    selection?.scope === scope
      ? (groups.find((group) => group.country.iso2 === selection.iso) ?? null)
      : null;
  if (selection && !selected) setSelection(null);
  const close = useCallback(() => setSelection(null), []);
  const select = useCallback((iso: string) => setSelection({ scope, iso }), [scope]);
  return { groups, selected, select, close };
}
