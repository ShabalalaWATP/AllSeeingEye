import type { Country } from '@/lib/api/geoSchemas';
import type { RadarAttackSnapshot } from '@/lib/api/cyber';

export interface RadarAttackCountry {
  country: Country;
  layer3: number | null;
  layer7: number | null;
}

/** Join provider-wide target billing-country shares without inventing incident positions. */
export function radarAttackCountries(
  snapshot: RadarAttackSnapshot | null,
  countries: Record<string, Country>,
): RadarAttackCountry[] {
  if (!snapshot || !['ready', 'partial', 'stale'].includes(snapshot.status)) return [];
  const byIso = new Map<string, RadarAttackCountry>();
  for (const layer of snapshot.layers) {
    for (const row of layer.countries) {
      const country = countries[row.country_iso];
      if (!country) continue;
      const item = byIso.get(row.country_iso) ?? { country, layer3: null, layer7: null };
      if (layer.layer === 'layer3') item.layer3 = row.share_percent;
      else item.layer7 = row.share_percent;
      byIso.set(row.country_iso, item);
    }
  }
  return [...byIso.values()].sort((a, b) => a.country.name.localeCompare(b.country.name));
}
