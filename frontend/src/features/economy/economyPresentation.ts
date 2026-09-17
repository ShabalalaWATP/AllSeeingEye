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
    // Compact financial labels use $ and K/M/B/T consistently across ICU versions.
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      notation: 'compact',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(value);
  }
  const compact = /people|persons|population/i.test(unit);
  const number = new Intl.NumberFormat(compact ? 'en-US' : 'en-GB', {
    notation: compact ? 'compact' : 'standard',
    maximumFractionDigits: /per [A-Z]{3}$/i.test(unit) ? 4 : 2,
  }).format(value);
  return /%|percent/i.test(unit) ? `${number}%` : number;
}

export function latestObservation(series: EconomySeries) {
  return [...series.points].reverse().find((point) => point.value !== null);
}

export function metricExplanation(id: string) {
  const explanations: Record<string, string> = {
    gdp_per_capita:
      'Economic output divided by population, measured in current US dollars. This is not a typical salary or household income, and exchange-rate changes affect comparisons.',
    population:
      'The estimated total resident population. Annual percentage change reflects population growth, not income or living standards.',
    exports:
      'Exports of goods and services as a share of GDP. This measures external sales relative to economic output, not the growth rate of exports.',
    imports:
      'Imports of goods and services as a share of GDP. Imports can support production and consumption; a higher share is not automatically a weakness.',
    current_account:
      'The current-account balance includes trade in goods and services, primary income and transfers, as a share of GDP. A surplus or deficit alone does not establish economic health.',
    government_debt:
      'Central government debt as a share of GDP. Coverage can exclude local government and other public bodies, so this is not general government debt or a complete public-sector debt measure.',
    investment:
      'Gross capital formation as a share of GDP, including fixed assets and changes in inventories. This measures investment in production, not stock-market investment returns.',
    manufacturing:
      'Manufacturing value added as a share of GDP. A changing share can reflect changes in manufacturing or in the rest of the economy; it is not manufacturing output growth.',
  };
  if (explanations[id]) return explanations[id];
  if (/MKTP.CD|^gdp$/i.test(id))
    return 'The annual value of goods and services produced, measured in current US dollars.';
  if (/KD.ZG|growth/i.test(id))
    return 'How much the economy grew or shrank from the previous year, after adjusting for inflation.';
  if (/CPI|inflation/i.test(id))
    return 'The annual change in consumer prices. A lower rate does not necessarily mean prices are falling.';
  if (/UEM|unemployment/i.test(id))
    return 'The share of the labour force without work, using the provider’s comparable estimate.';
  if (/^(GBP|USD|CNY|RUB|IRR)$/.test(id))
    return 'Units of this currency for one euro. Reference rates are daily observations, not trading quotes.';
  return 'A published observation from the named provider. Read the stated unit, observation period and original methodology before comparing values.';
}
