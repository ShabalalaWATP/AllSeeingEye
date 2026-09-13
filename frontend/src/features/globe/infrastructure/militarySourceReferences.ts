import registry from './military_infrastructure_sources.json';
import type { Country } from '@/lib/api/geoSchemas';

export interface MilitarySource {
  id: string;
  publisher: string;
  title: string;
  url: string;
  published_at: string | null;
  assertion_scope: string;
  limitation: string;
}

export interface MilitaryCountryReference {
  id: string;
  name: string;
  country: Country;
  sources: MilitarySource[];
}

/** These are country source indexes, not installation or unit positions. */
export function militaryCountryReferences(
  countries: Record<string, Country>,
): MilitaryCountryReference[] {
  return registry.countries.flatMap((code) => {
    const country = countries[code];
    if (
      !country ||
      !Number.isFinite(country.centroid[0]) ||
      !Number.isFinite(country.centroid[1]) ||
      Math.abs(country.centroid[0]) > 180 ||
      Math.abs(country.centroid[1]) > 90
    )
      return [];
    return [
      {
        id: code,
        name: country.name,
        country,
        sources: registry.sources.filter((source) => source.country_codes.includes(code)),
      },
    ];
  });
}
