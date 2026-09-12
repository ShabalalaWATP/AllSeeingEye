import { fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it } from 'vitest';
import type { EconomyRegion, EconomySeries } from '@/lib/api/economy';
import { economySeries, economySnapshot } from '@/test/fixtures.economy';
import { compareCountries } from './comparisonData';
import { CountryComparison } from './CountryComparison';
import { currencyAnalysis } from './currencyCalculations';
import { CurrencyAnalysis } from './CurrencyAnalysis';

const country = (id: string, values: (number | null)[]): EconomyRegion => ({
  id,
  name: id,
  series: [
    {
      ...economySeries,
      id: 'growth',
      name: 'GDP growth',
      unit: '% annual change',
      points: values.map((value, index) => ({ date: String(2023 + index), value })),
    },
  ],
});
const rates = (id: string, values: (number | null)[]): EconomySeries => ({
  ...economySeries,
  id,
  name: `${id} per euro`,
  unit: `${id} per EUR`,
  frequency: 'daily',
  points: values.map((value, index) => ({
    date: ['2026-07-01', '2026-09-01', '2026-09-02'][index]!,
    value,
  })),
});
it('defaults to the latest fully comparable year rather than mixing latest observations', () => {
  const result = compareCountries(
    [country('GB', [1, 2, null]), country('US', [2, 3, 4]), country('WORLD', [9, 9, 9])],
    'growth',
  );
  expect(result.selected).toEqual({ year: '2024', count: 2 });
  expect(result.rows.map((r) => r.value)).toEqual([2, 3]);
  expect(result.rows.map((r) => r.previous)).toEqual([1, 2]);
  expect(result.world).toBe(9);
  expect(
    compareCountries(
      [country('GB', [1, 2, null]), country('US', [2, 3, 4])],
      'growth',
      '2025',
    ).rows.map((r) => r.value),
  ).toEqual([null, 4]);
});
it('chooses widest coverage then most recent year and respects genuine negative and zero values', () => {
  const regions = [
    country('GB', [null, 0, 1]),
    country('US', [null, -2, null]),
    country('CN', [null, null, 2]),
  ];
  const result = compareCountries(regions, 'growth');
  expect(result.selected?.year).toBe('2025');
  expect(compareCountries(regions, 'growth', '2024').ranked.map((r) => r.value)).toEqual([0, -2]);
});
it('does not rank unavailable or mismatched-unit observations', () => {
  const unavailable = country('US', [1, 2, 3]);
  unavailable.series[0]!.status = 'unavailable';
  const incompatible = country('CN', [1, 2, 3]);
  incompatible.series[0]!.unit = 'Current US dollars';
  const result = compareCountries([country('GB', [1, 2, 3]), unavailable, incompatible], 'growth');
  expect(result.ranked).toHaveLength(1);
  expect(result.rows.slice(1).map((r) => r.value)).toEqual([null, null]);
  expect(compareCountries([], 'gdp').selected).toBeUndefined();
});
it('renders signed comparisons, selects actual years and exposes source-labelled values', () => {
  render(
    <CountryComparison
      regions={[country('GB', [1, 0, null]), country('US', [2, -2, 4])]}
      focus="GB"
    />,
  );
  expect(screen.getByRole('combobox', { name: 'Comparison year' })).toHaveValue('2024');
  expect(screen.getByText(/highest recorded value/)).toHaveTextContent('GB');
  fireEvent.change(screen.getByRole('combobox', { name: 'Comparison year' }), {
    target: { value: '2025' },
  });
  expect(screen.getByText(/too few observations/)).toBeInTheDocument();
  expect(
    within(screen.getByRole('table')).getAllByRole('link', { name: 'World Bank' }),
  ).toHaveLength(2);
});
it('handles ties, all missing data and indicator changes without invented rankings', () => {
  const { rerender } = render(
    <CountryComparison regions={economySnapshot.regions} focus="WORLD" />,
  );
  expect(screen.getByText(/report the same value/)).toBeInTheDocument();
  fireEvent.change(screen.getByRole('combobox', { name: 'Comparison indicator' }), {
    target: { value: 'unemployment' },
  });
  expect(screen.getByRole('combobox', { name: 'Comparison year' })).toHaveTextContent(
    'No shared observations',
  );
  rerender(<CountryComparison regions={[]} focus="WORLD" />);
  expect(screen.getByText(/Country comparison data is currently unavailable/)).toBeInTheDocument();
});
it('calculates quote per base on identical dates and uses correct strength direction', () => {
  const result = currencyAnalysis(
    [rates('GBP', [0.8, 1, 1]), rates('USD', [1, 1.2, 1.3])],
    'GBP',
    'USD',
    90,
  )!;
  expect(result.series.points.map((p) => p.value)).toEqual([1.25, 1.2, 1.3]);
  expect(result.change).toBeCloseTo(4);
  expect(result.low).toBe(1.2);
  expect(result.high).toBe(1.3);
  expect(
    currencyAnalysis([rates('GBP', [0.8, 1, 1]), rates('USD', [1, 1.2, 1.3])], 'USD', 'GBP', 90)!
      .change,
  ).toBeCloseTo(-3.8461538);
});
it('uses the window ending at the last matching date without filling missing or zero rates', () => {
  const values = [rates('GBP', [0.8, 0, 1]), rates('USD', [1, 1.2, 1.3])];
  const result = currencyAnalysis(values, 'GBP', 'USD', 30)!;
  expect(result.series.points.map((p) => p.value)).toEqual([null, 1.3]);
  expect(result.change).toBeNull();
  expect(result.count).toBe(1);
});
it('supports EUR as the exact base and propagates stale status', () => {
  const gbp = { ...rates('GBP', [0.8, 1, 1]), status: 'stale' as const };
  expect(currencyAnalysis([gbp], 'EUR', 'GBP', 90)!.series.points[0]!.value).toBe(0.8);
  expect(currencyAnalysis([gbp], 'GBP', 'EUR', 90)!.series.points[0]!.value).toBe(1.25);
  expect(currencyAnalysis([gbp], 'GBP', 'EUR', 90)!.series.status).toBe('stale');
});
it('returns no derived rate for identical currencies, unavailable inputs or disjoint dates', () => {
  expect(currencyAnalysis([], 'EUR', 'EUR', 90)).toBeNull();
  expect(currencyAnalysis([], 'GBP', 'USD', 90)).toBeNull();
  expect(
    currencyAnalysis([rates('GBP', [1, null, null]), rates('USD', [null, 2, 3])], 'GBP', 'USD', 90),
  ).toBeNull();
  expect(
    currencyAnalysis([{ ...rates('GBP', [1, 2, 3]), status: 'unavailable' }], 'GBP', 'EUR', 90),
  ).toBeNull();
});
it('shows calculated currency insights and updates controls without requiring chart activation', () => {
  render(<CurrencyAnalysis items={[rates('GBP', [0.8, 1, 1]), rates('USD', [1, 1.2, 1.3])]} />);
  expect(screen.getByRole('img', { name: /GBP \/ USD history/ })).toBeInTheDocument();
  expect(screen.getByText(/strengthened/)).toHaveTextContent('4.00%');
  fireEvent.change(screen.getByRole('combobox', { name: 'Currency analysis period' }), {
    target: { value: '30' },
  });
  expect(screen.getByText(/strengthened/)).toHaveTextContent('8.33%');
  fireEvent.change(screen.getByRole('combobox', { name: 'Base currency' }), {
    target: { value: 'USD' },
  });
  expect(screen.getByText(/Choose two different currencies/)).toBeInTheDocument();
  fireEvent.change(screen.getByRole('combobox', { name: 'Quote currency' }), {
    target: { value: 'GBP' },
  });
  expect(screen.getByText(/weakened/)).toBeInTheDocument();
});
it('explains unavailable, one-observation and unchanged pairs', () => {
  const { rerender } = render(<CurrencyAnalysis items={[]} />);
  expect(screen.getByText(/No matching published dates/)).toBeInTheDocument();
  rerender(
    <CurrencyAnalysis items={[rates('GBP', [null, null, 1]), rates('USD', [null, null, 2])]} />,
  );
  expect(screen.getByText(/Only one matching observation/)).toBeInTheDocument();
  rerender(<CurrencyAnalysis items={[rates('GBP', [1, 1, 1]), rates('USD', [2, 2, 2])]} />);
  expect(screen.getByText(/was unchanged/)).toBeInTheDocument();
});
