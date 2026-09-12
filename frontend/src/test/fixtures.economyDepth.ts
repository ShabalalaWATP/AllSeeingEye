/** Deterministic visual/test data only. Never used by production loaders. */
import type { EconomySnapshot } from '@/lib/api/economy';
import { economySeries, economySnapshot } from './fixtures.economy';

const metrics = [
  ['gdp', 'GDP', 'Current US dollars', 3.3e12],
  ['growth', 'GDP growth', '% annual change', 2.4],
  ['inflation', 'Consumer price inflation', '% annual change', 3.8],
  ['unemployment', 'Unemployment', '% of labour force', 4.2],
  ['gdp_per_capita', 'GDP per capita', 'Current US dollars', 49_000],
  ['population', 'Population', 'People', 68_000_000],
  ['exports', 'Exports of goods and services', '% of GDP', 32],
  ['imports', 'Imports of goods and services', '% of GDP', 35],
  ['current_account', 'Current account balance', '% of GDP', -1.4],
  ['government_debt', 'Central government debt', '% of GDP', 84],
  ['investment', 'Gross capital formation', '% of GDP', 22],
  ['manufacturing', 'Manufacturing value added', '% of GDP', 14],
] as const;

export const economyDepthSnapshot: EconomySnapshot = {
  ...economySnapshot,
  regions: economySnapshot.regions.map((region, index) => ({
    ...region,
    series: metrics.map(([id, name, unit, base]) => ({
      ...economySeries,
      id,
      name,
      unit,
      points: Array.from({ length: 12 }, (_, year) => ({
        date: String(2014 + year),
        value:
          region.id === 'IR' && id === 'government_debt'
            ? null
            : base * (1 + index * 0.13) * (0.8 + year * 0.025),
      })),
      status: region.id === 'IR' && id === 'government_debt' ? 'unavailable' : 'available',
    })),
  })),
  fx: economySnapshot.fx.map((series, index) => ({
    ...series,
    points:
      series.status === 'unavailable'
        ? []
        : Array.from({ length: 60 }, (_, day) => ({
            date: new Date(Date.UTC(2026, 6, 14 + day)).toISOString().slice(0, 10),
            value: [0.85, 1.16, 7.77][index]! * (1 + day * 0.0003 + Math.sin(day / 6) * 0.005),
          })),
  })),
};
