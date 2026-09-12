import type { EconomyRegion, EconomySeries } from '@/lib/api/economy';

export function periodValue(series: EconomySeries | undefined, year: string): number | null {
  if (!series || series.status === 'unavailable') return null;
  return series.points.find((point) => point.date === year)?.value ?? null;
}

/** Choose an actual shared period. Never compare each country's different latest year. */
export function compareCountries(regions: readonly EconomyRegion[], metric: string, choice = '') {
  const countries = regions.filter((region) => region.id !== 'WORLD');
  const series = countries.map((region) => region.series.find((item) => item.id === metric));
  const definition = series.find((item) => item !== undefined);
  const compatible = series.map((item) => (item?.unit === definition?.unit ? item : undefined));
  const years = [
    ...new Set(compatible.flatMap((item) => item?.points.map((point) => point.date) ?? [])),
  ]
    .filter((year) => /^\d{4}$/.test(year))
    .sort((a, b) => b.localeCompare(a))
    .map((year) => ({
      year,
      count: compatible.filter((item) => periodValue(item, year) !== null).length,
    }))
    .filter((period) => period.count > 0);
  const widest = [...years].sort((a, b) => b.count - a.count || b.year.localeCompare(a.year))[0];
  const selected = years.find((period) => period.year === choice) ?? widest;
  const rows = countries.map((country, index) => ({
    id: country.id,
    name: country.name,
    series: compatible[index],
    value: selected ? periodValue(compatible[index], selected.year) : null,
    previous: selected ? periodValue(compatible[index], String(Number(selected.year) - 1)) : null,
  }));
  const available = rows.filter((row): row is typeof row & { value: number } => row.value !== null);
  const ranked = [...available].sort((a, b) => b.value - a.value);
  const worldSeries = regions
    .find((region) => region.id === 'WORLD')
    ?.series.find((item) => item.id === metric);
  return {
    definition,
    years,
    selected,
    rows,
    ranked,
    world:
      selected && worldSeries?.unit === definition?.unit
        ? periodValue(worldSeries, selected.year)
        : null,
  };
}
