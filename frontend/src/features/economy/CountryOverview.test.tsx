import { render, screen, within } from '@testing-library/react';
import { expect, it } from 'vitest';
import type { EconomyRegion, EconomySeries } from '@/lib/api/economy';
import { economySeries, economySnapshot } from '@/test/fixtures.economy';
import { CountryOverview } from './CountryOverview';
import { CountryInsights } from './CountryInsights';
import { countryOverview } from './countryOverviewData';
import { countryInsights } from './economicChanges';

function indicator(id: string, value: number | null, year = '2025'): EconomySeries {
  return {
    ...economySeries,
    id,
    unit: id === 'current_account' ? '% of GDP' : '% annual change',
    source_url: `https://data.worldbank.org/indicator/${id}`,
    points: [{ date: year, value }],
  };
}
const region = (series: EconomySeries[]): EconomyRegion => ({
  id: 'GB',
  name: 'United Kingdom',
  series,
});

it('starts with a short dated overview and attributes each included indicator', () => {
  render(<CountryOverview region={economySnapshot.regions[1]!} />);
  const overview = screen.getByRole('region', { name: 'United Kingdom economic overview' });
  expect(overview).toHaveTextContent('Real output grew by 1.25% in 2025');
  expect(overview).toHaveTextContent('consumer prices rose by 2.6% in 2025');
  expect(overview).toHaveTextContent('separate from the selected news summary period');
  expect(within(overview).getByRole('link', { name: 'Growth: World Bank' })).toHaveAttribute(
    'href',
    economySeries.source_url,
  );
  expect(within(overview).queryByRole('link', { name: 'Unemployment: World Bank' })).toBeNull();
});

it('preserves different observation years and distinguishes old observations from cached retrievals', () => {
  const summary = countryOverview(
    region([
      indicator('growth', -0.51234, '2021'),
      indicator('inflation', 6.25, '2024'),
      indicator('unemployment', 4.1234, '2023'),
      { ...indicator('current_account', -2.5, '2025'), status: 'stale' },
    ]),
    2026,
  );
  expect(summary.text).toBe(
    'Real output contracted by 0.51% in 2021, while consumer prices rose by 6.25% in 2024. Unemployment was 4.12% of the labour force in 2023, while the current account recorded a deficit of 2.5% of GDP in 2025.',
  );
  expect(summary.hasOlderObservations).toBe(true);
  expect(summary.cached).toBe(true);
  expect(summary.sources).toHaveLength(4);
});

it('makes sparse country data useful without filling missing measures or implying a current trend', () => {
  const summary = countryOverview(
    region([
      indicator('growth', null),
      indicator('inflation', -1.5),
      indicator('current_account', 3),
    ]),
    2026,
  );
  expect(summary.text).toBe(
    'Consumer prices fell by 1.5% in 2025, while the current account recorded a surplus of 3% of GDP in 2025.',
  );
  expect(summary.text).not.toMatch(/growth|unemployment|accelerat|today/i);
  expect(summary.hasOlderObservations).toBe(false);
  expect(summary.cached).toBe(false);
});

it('does not describe zero observations as growth, deflation or an external deficit', () => {
  const summary = countryOverview(
    region([indicator('growth', 0), indicator('inflation', 0), indicator('current_account', 0)]),
  );
  expect(summary.text).toContain('Real output was unchanged in 2025');
  expect(summary.text).toContain('average consumer prices were unchanged in 2025');
  expect(summary.text).toContain('The current account was balanced in 2025');
});

it('excludes unavailable retained points, daily inputs and malformed annual periods from all prose', () => {
  const unavailable = region([
    { ...indicator('growth', 99), status: 'unavailable' },
    { ...indicator('inflation', 88), frequency: 'daily' },
    indicator('unemployment', 77, '2025-Q1'),
    indicator('current_account', null),
  ]);
  expect(countryOverview(unavailable).sources).toEqual([]);
  expect(countryInsights(unavailable)).toEqual([]);
  render(<CountryOverview region={unavailable} />);
  expect(screen.getByText(/too few published observations/)).toBeInTheDocument();
  expect(screen.queryByRole('link')).toBeNull();
  expect(screen.getByRole('region')).not.toHaveTextContent(/99%|88%|77%/);
});

it('labels an older cached overview while retaining exact source attribution', () => {
  render(
    <CountryOverview region={region([{ ...indicator('growth', 2, '2020'), status: 'stale' }])} />,
  );
  expect(screen.getByText(/Some observations are more than two years old/)).toHaveTextContent(
    'Some source data is being served from an older cache',
  );
  expect(screen.getByRole('link')).toHaveAttribute(
    'href',
    'https://data.worldbank.org/indicator/growth',
  );
});

it('separates recorded results from readable explanations and marks cached insight sources', () => {
  render(
    <CountryInsights
      region={region([
        { ...indicator('inflation', 2.6), status: 'stale' },
        indicator('unemployment', 4.2),
      ])}
    />,
  );
  const articles = screen.getAllByRole('article');
  expect(within(articles[0]!).getByText('Inflation was 2.6% in 2025.')).toBeInTheDocument();
  expect(within(articles[0]!).getByText(/prices still rose/)).toBeInTheDocument();
  expect(articles[0]).toHaveTextContent('Cached source data');
  expect(articles[1]).toHaveTextContent('Unemployment was 4.2% of the labour force in 2025');
  expect(articles[1]).toHaveTextContent('not of the whole population');
  expect(within(articles[1]!).getByRole('link')).toHaveAttribute(
    'href',
    'https://data.worldbank.org/indicator/unemployment',
  );
});
