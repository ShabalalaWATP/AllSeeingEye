import { expect, it } from 'vitest';
import { economySeries } from '@/test/fixtures.economy';
import type { EconomyRegion, EconomySeries } from '@/lib/api/economy';
import {
  annualChange,
  countryInsights,
  formatAnnualChange,
  observationAge,
} from './economicChanges';
import { formatEconomicValue, metricExplanation } from './economyPresentation';

function series(id: string, unit: string, values: [number | null, number | null]): EconomySeries {
  return {
    ...economySeries,
    id,
    unit,
    points: [
      { date: '2024', value: values[0] },
      { date: '2025', value: values[1] },
    ],
  };
}
function region(items: EconomySeries[]): EconomyRegion {
  return { id: 'GB', name: 'United Kingdom', series: items };
}

it('distinguishes rate changes in percentage points from relative growth of positive amounts', () => {
  const rates = annualChange(series('growth', '% annual change', [-2, 1]));
  expect(rates).toEqual({ value: 3, unit: 'percentage points', from: '2024', to: '2025' });
  expect(formatAnnualChange(rates!)).toBe('+3 pp vs 2024');
  const amounts = annualChange(series('gdp', 'Current US dollars', [100, 120]));
  expect(amounts?.value).toBe(20);
  expect(formatAnnualChange(amounts!)).toBe('+20% vs 2024');
  expect(annualChange(series('gdp', 'Current US dollars', [100, 0]))?.value).toBe(-100);
  expect(formatAnnualChange(annualChange(series('population', 'People', [10, 10]))!)).toBe(
    '0% vs 2024',
  );
});

it('does not turn missing, non-consecutive or non-annual observations into annual changes', () => {
  expect(annualChange(economySeries)).toBeNull();
  expect(annualChange({ ...economySeries, points: [] })).toBeNull();
  expect(annualChange({ ...economySeries, points: [{ date: '2024', value: null }] })).toBeNull();
  expect(
    annualChange({
      ...economySeries,
      points: [
        { date: '2023', value: 50 },
        { date: '2025', value: 100 },
      ],
    }),
  ).toBeNull();
  expect(annualChange({ ...economySeries, points: [{ date: '2025-Q1', value: 100 }] })).toBeNull();
  expect(annualChange({ ...series('USD', 'USD per EUR', [1, 2]), frequency: 'daily' })).toBeNull();
});

it('omits misleading percentage growth from negative or zero monetary bases', () => {
  expect(annualChange(series('gdp', 'Current US dollars', [0, 10]))).toBeNull();
  expect(annualChange(series('gdp', 'Current US dollars', [-10, 10]))).toBeNull();
  expect(annualChange(series('gdp', 'Current US dollars', [10, -10]))).toBeNull();
  expect(annualChange(series('current_account', '% of GDP', [-5, -2]))?.value).toBe(3);
  expect(annualChange(series('growth', '% annual change', [-1e308, 1e308]))).toBeNull();
  expect(annualChange(series('gdp', 'Current US dollars', [1e-308, 1e308]))).toBeNull();
});

it('labels older observation years without confusing retrieval time with the observation', () => {
  expect(observationAge('2021', 2026)).toBe('5 years old');
  expect(observationAge('2024', 2026)).toBe('');
  expect(observationAge('2027', 2026)).toBe('');
  expect(observationAge('2026-09-12', 2026)).toBe('');
});

it('explains slowing inflation as prices still rising and debt as central-government coverage', () => {
  const insights = countryInsights(
    region([
      series('growth', '% annual change', [1, -0.5]),
      series('inflation', '% annual change', [6, 3]),
      series('current_account', '% of GDP', [-2, -3]),
      series('government_debt', '% of GDP', [70, 75]),
    ]),
  );
  expect(insights[0]?.text).toContain('contracted in 2025');
  expect(insights[1]?.explanation).toContain('prices still rose');
  expect(insights[1]?.explanation).toContain('rate eased (-3 pp vs 2024)');
  expect(insights[2]?.text).toContain('a deficit of 3% of GDP');
  expect(insights[3]?.text).toContain('central government debt');
  expect(insights[3]?.explanation).toContain('may exclude other government bodies');
});

it('handles deflation, zero growth, external balance and missing readouts without inventing direction', () => {
  const flat = countryInsights(
    region([
      series('growth', '% annual change', [null, 0]),
      series('inflation', '% annual change', [-1, -1]),
      series('current_account', '% of GDP', [1, 0]),
    ]),
  );
  expect(flat[0]?.text).toContain('was unchanged in 2025');
  expect(flat[0]?.explanation).toContain('preceding-year growth is unavailable');
  expect(flat[1]?.explanation).toContain('prices fell');
  expect(flat[1]?.explanation).toContain('rate was unchanged');
  expect(flat[2]?.text).toContain('a balance of 0%');
  const rising = countryInsights(
    region([
      series('growth', '% annual change', [1, 2]),
      series('inflation', '% annual change', [-1, 0]),
      series('current_account', '% of GDP', [1, 2]),
    ]),
  );
  expect(rising[0]?.text).toContain('expanded');
  expect(rising[1]?.explanation).toContain('Average consumer prices were unchanged');
  expect(rising[1]?.explanation).toContain('rate increased');
  expect(rising[2]?.text).toContain('a surplus of 2%');
  expect(countryInsights(region([series('inflation', '% annual change', [null, null])]))).toEqual(
    [],
  );
});

it('explains each new metric, preserves currency precision and keeps population readable', () => {
  expect(formatEconomicValue(1_400_000_000, 'People')).toBe('1.4B');
  expect(formatEconomicValue(1.2637, 'USD per GBP')).toBe('1.2637');
  expect(metricExplanation('gdp_per_capita')).toContain('not a typical salary');
  expect(metricExplanation('population')).toContain('resident population');
  expect(metricExplanation('exports')).toContain('not the growth rate');
  expect(metricExplanation('imports')).toContain('not automatically a weakness');
  expect(metricExplanation('current_account')).toContain('primary income');
  expect(metricExplanation('government_debt')).toContain('not general government debt');
  expect(metricExplanation('investment')).toContain('not stock-market investment returns');
  expect(metricExplanation('manufacturing')).toContain('not manufacturing output growth');
  expect(metricExplanation('CNY')).toContain('for one euro');
  expect(metricExplanation('unknown')).not.toContain('euro');
});
