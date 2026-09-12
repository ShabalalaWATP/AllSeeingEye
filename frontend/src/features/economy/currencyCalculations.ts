import type { EconomySeries } from '@/lib/api/economy';

export const FX_CODES = ['EUR', 'GBP', 'USD', 'CNY'] as const;
export type FxCode = (typeof FX_CODES)[number];

/** Cross-rate = quote units per EUR / base units per EUR, on matching dates only. */
export function currencyAnalysis(
  items: readonly EconomySeries[],
  base: FxCode,
  quote: FxCode,
  days: number,
) {
  const get = (id: string) => items.find((item) => item.id === id && item.status !== 'unavailable');
  const baseSeries = get(base),
    quoteSeries = get(quote);
  if (base === quote || (base !== 'EUR' && !baseSeries) || (quote !== 'EUR' && !quoteSeries))
    return null;
  const source = quoteSeries ?? baseSeries;
  if (!source) return null;
  const dates = [
    ...new Set(
      [...(baseSeries?.points ?? []), ...(quoteSeries?.points ?? [])].map((point) => point.date),
    ),
  ].sort();
  const value = (series: EconomySeries | undefined, code: string, date: string) =>
    code === 'EUR' ? 1 : series?.points.find((point) => point.date === date)?.value;
  const all = dates.map((date) => {
    const a = value(baseSeries, base, date),
      b = value(quoteSeries, quote, date);
    return {
      date,
      value: typeof a === 'number' && a > 0 && typeof b === 'number' && b > 0 ? b / a : null,
    };
  });
  const last = all.findLast((point) => point.value !== null);
  if (!last) return null;
  const end = Date.parse(`${last.date}T00:00:00Z`);
  const points = all.filter(
    (point) =>
      Date.parse(`${point.date}T00:00:00Z`) >= end - (days - 1) * 86_400_000 &&
      point.date <= last.date,
  );
  const observed = points.filter(
    (point): point is { date: string; value: number } => point.value !== null,
  );
  const first = observed[0];
  if (!first) return null;
  const change =
    observed.length > 1 && last.value !== null ? (last.value / first.value - 1) * 100 : null;
  const stale = baseSeries?.status === 'stale' || quoteSeries?.status === 'stale';
  const series: EconomySeries = {
    ...source,
    id: `${base}-${quote}`,
    name: `${base} / ${quote}`,
    unit: `${quote} per ${base}`,
    status: stale ? 'stale' : 'available',
    points,
    note: `Calculated from matching ECB daily reference dates: ${quote} per euro divided by ${base} per euro. EUR is 1. No forward-filling or live quote substitution.`,
  };
  return {
    series,
    first,
    last,
    change,
    count: observed.length,
    low: Math.min(...observed.map((p) => p.value)),
    high: Math.max(...observed.map((p) => p.value)),
  };
}
