import { fireEvent, render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { economySeries, economySnapshot } from '@/test/fixtures.economy';
import { EconomicChart } from './EconomicChart';
import { CountryEconomy } from './CountryEconomy';
import { CurrencyContext } from './CurrencyContext';
import { formatEconomicValue, metricExplanation } from './economyPresentation';

it('formats actual backend GDP, percentage and reference-rate units distinctly', () => {
  expect(formatEconomicValue(3.3e12, 'Current US dollars')).toMatch(/\$3\.3T/);
  expect(formatEconomicValue(0.8547, 'GBP per EUR')).toBe('0.8547');
  expect(formatEconomicValue(1.1725, 'USD per EUR')).toBe('1.1725');
  expect(formatEconomicValue(-1.25, '% annual change')).toBe('-1.25%');
  expect(formatEconomicValue(null, '% annual change')).toBe('Not available');
});

it('preserves missing years as gaps and exposes unrounded observations in the table', () => {
  render(<EconomicChart series={economySeries} />);
  const line = screen.getByRole('img', { name: /GDP history/ }).querySelector('path');
  expect(line?.getAttribute('d')?.match(/M/g)).toHaveLength(2);
  expect(screen.getByRole('table', { name: /GDP observations/ })).toHaveTextContent(
    '3,300,000,000,000',
  );
  fireEvent.change(screen.getByRole('slider'), { target: { value: '1' } });
  expect(screen.getAllByText('Not available').length).toBeGreaterThan(0);
  fireEvent.change(screen.getByRole('slider'), { target: { value: '0' } });
  expect(screen.getByLabelText('Selected observation value')).toHaveTextContent(/\$3\.1T/);
});

it('handles a constant series and retains currency precision in its data table', () => {
  render(
    <EconomicChart
      series={{
        ...economySeries,
        name: 'FX',
        unit: 'USD per EUR',
        frequency: 'daily',
        points: [
          { date: '2026-09-10', value: 1.172567 },
          { date: '2026-09-11', value: 1.172567 },
        ],
      }}
    />,
  );
  expect(screen.getByRole('img').querySelector('path')?.getAttribute('d')).not.toMatch(
    /NaN|Infinity/,
  );
  expect(screen.getByRole('table')).toHaveTextContent('1.172567');
});

it('starts the date control at the latest published value when the final year is missing', () => {
  render(
    <EconomicChart
      series={{
        ...economySeries,
        points: [...economySeries.points, { date: '2026', value: null }],
      }}
    />,
  );
  expect(screen.getByRole('slider')).toHaveValue('2');
  expect(screen.getByLabelText('Selected observation value')).toHaveTextContent(/\$3\.3T/);
  fireEvent.change(screen.getByRole('slider'), { target: { value: '3' } });
  expect(screen.getByLabelText('Selected observation value')).toHaveTextContent('Not available');
});

it('shows missing series instead of plotting invented zeroes', () => {
  render(<EconomicChart series={{ ...economySeries, points: [{ date: '2025', value: null }] }} />);
  expect(screen.getByText(/No published observations/)).toBeInTheDocument();
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
});

it('does not magnify floating-point cross-rate noise into apparent currency swings', () => {
  render(
    <EconomicChart
      series={{
        ...economySeries,
        frequency: 'daily',
        unit: 'USD per GBP',
        points: [
          { date: '2026-09-10', value: 1.364705882352941 },
          { date: '2026-09-11', value: 1.3647058823529412 },
        ],
      }}
    />,
  );
  const positions = [...screen.getByRole('img').querySelectorAll('circle')].map((point) =>
    Number(point.getAttribute('cy')),
  );
  expect(Math.abs(positions[0]! - positions[1]!)).toBeLessThan(0.01);
  expect(screen.getByRole('table')).toHaveTextContent('1.3647058823529412');
});

it('switches economic metrics and explains observation dates and units', async () => {
  const user = userEvent.setup();
  render(<CountryEconomy region={economySnapshot.regions[1]} />);
  await user.click(screen.getByRole('button', { name: /GDP growth/ }));
  expect(screen.getByRole('img', { name: /GDP growth history/ })).toBeInTheDocument();
  expect(screen.getByText(/after adjusting for inflation/)).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: /Unemployment/ }));
  expect(screen.getByText(/No published observations/)).toBeInTheDocument();
  expect(metricExplanation('inflation')).toMatch(/prices are falling/);
  expect(metricExplanation('gdp')).toMatch(/goods and services/);
});

it('switches supported currencies without treating missing RUB or IRR as zero', async () => {
  const user = userEvent.setup();
  render(<CurrencyContext items={economySnapshot.fx} />);
  expect(screen.getByRole('button', { name: /RUB per euro/ })).toBeDisabled();
  expect(screen.getByRole('button', { name: /IRR per euro/ })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: /USD per euro/ }));
  expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(3);
  expect(screen.getByRole('img', { name: /USD per euro history/ })).toBeInTheDocument();
});

it('keeps unavailable country and FX states legible', () => {
  render(
    <>
      <CountryEconomy region={undefined} />
      <CurrencyContext items={[]} />
    </>,
  );
  expect(screen.getByText(/Official indicators for this region/)).toBeInTheDocument();
  expect(screen.getByText(/Currency history is currently unavailable/)).toBeInTheDocument();
});
