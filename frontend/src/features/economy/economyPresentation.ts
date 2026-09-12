import type { EconomySeries } from '@/lib/api/economy';

export const REGIONS = [
  {
    id: 'WORLD',
    name: 'Worldwide',
    short: 'Global',
    detail: 'Growth, prices, trade and the forces connecting markets.',
  },
  {
    id: 'GB',
    name: 'United Kingdom',
    short: 'UK',
    detail: 'Sterling, household costs, public finances and UK businesses.',
  },
  {
    id: 'US',
    name: 'United States',
    short: 'USA',
    detail: 'The dollar, interest rates, employment and major listed companies.',
  },
  {
    id: 'RU',
    name: 'Russia',
    short: 'Russia',
    detail: 'Energy exports, inflation, trade restrictions and the domestic economy.',
  },
  {
    id: 'CN',
    name: 'China',
    short: 'China',
    detail: 'Manufacturing, domestic demand, property and international trade.',
  },
  {
    id: 'IR',
    name: 'Iran',
    short: 'Iran',
    detail: 'Oil revenues, prices, currency pressures and trade restrictions.',
  },
] as const;
export type RegionCode = (typeof REGIONS)[number]['id'];

export function formatEconomicValue(value: number | null, unit: string): string {
  if (value === null) return 'Not available';
  if (/^(current )?us dollars$|^usd$|^us\$$/i.test(unit)) {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'USD',
      notation: 'compact',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(value);
  }
  const number = new Intl.NumberFormat('en-GB', {
    maximumFractionDigits: /per EUR/i.test(unit) ? 4 : 2,
  }).format(value);
  return /%|percent/i.test(unit) ? `${number}%` : number;
}

export function latestObservation(series: EconomySeries) {
  return [...series.points].reverse().find((point) => point.value !== null);
}

export function metricExplanation(id: string) {
  if (/MKTP.CD|^gdp$/i.test(id))
    return 'The annual value of goods and services produced, measured in current US dollars.';
  if (/KD.ZG|growth/i.test(id))
    return 'How much the economy grew or shrank from the previous year, after adjusting for inflation.';
  if (/CPI|inflation/i.test(id))
    return 'The annual change in consumer prices. A lower rate does not necessarily mean prices are falling.';
  if (/UEM|unemployment/i.test(id))
    return 'The share of the labour force without work, using the provider’s comparable estimate.';
  return 'Units of this currency for one euro. Reference rates are daily observations, not trading quotes.';
}
