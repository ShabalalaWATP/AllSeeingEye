import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { economySeries, economySnapshot } from '@/test/fixtures.economy';
import type { EconomyRegion } from '@/lib/api/economy';
import { CountryEconomy } from './CountryEconomy';
import { IndicatorSparkline } from './IndicatorSparkline';

const extended: EconomyRegion = {
  ...economySnapshot.regions[1]!,
  series: [
    ...economySnapshot.regions[1]!.series,
    ...[
      ['gdp_per_capita', 'GDP per person', 'Current US dollars'],
      ['population', 'Population', 'People'],
      ['exports', 'Exports of goods and services', '% of GDP'],
      ['imports', 'Imports of goods and services', '% of GDP'],
      ['current_account', 'Current-account balance', '% of GDP'],
      ['manufacturing', 'Manufacturing value added', '% of GDP'],
      ['investment', 'Gross capital formation', '% of GDP'],
      ['government_debt', 'Central government debt', '% of GDP'],
    ].map(([id, name, unit]) => ({
      ...economySeries,
      id: id!,
      name: name!,
      unit: unit!,
      points: [
        { date: '2024', value: 15 },
        { date: '2025', value: 17 },
      ],
    })),
  ],
};

it('loads every available miniature history with clear groups, dates and a selected detailed chart', async () => {
  const user = userEvent.setup();
  const { container } = render(<CountryEconomy region={extended} />);
  expect(screen.getByText('11/12')).toBeInTheDocument();
  expect(screen.getByText('Output and living standards')).toBeInTheDocument();
  expect(screen.getByText('Trade and industry')).toBeInTheDocument();
  expect(screen.getByText('Public finances and investment')).toBeInTheDocument();
  expect(container.querySelectorAll('svg[aria-hidden="true"]')).toHaveLength(11);
  expect(screen.getAllByRole('img')).toHaveLength(1);
  await user.click(screen.getByRole('button', { name: /Central government debt/ }));
  expect(screen.getByRole('img', { name: /Central government debt history/ })).toBeInTheDocument();
  expect(screen.getByText(/this is not general government debt/)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'View original data' })).toHaveAttribute(
    'href',
    economySeries.source_url,
  );
  expect(
    screen.getByRole('region', { name: /United Kingdom calculated insights/ }),
  ).toHaveTextContent('What the data shows');
});

it('keeps absent observations and old cached periods visible and explains unknown series generically', async () => {
  const user = userEvent.setup();
  render(
    <CountryEconomy
      region={{
        id: 'IR',
        name: 'Iran',
        series: [
          {
            ...economySeries,
            id: 'unknown',
            name: 'Additional measure',
            status: 'stale',
            points: [{ date: '2020', value: 50 }],
          },
          { ...economySeries, id: 'unemployment', name: 'Unemployment', points: [] },
        ],
      }}
    />,
  );
  expect(screen.getByText('1/2')).toBeInTheDocument();
  expect(screen.getByText(/1 series served from an older cache/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Additional measure/ })).toHaveTextContent(
    'Observation: 2020',
  );
  expect(screen.getByRole('button', { name: /Additional measure/ })).toHaveTextContent('years old');
  expect(screen.getByText('Other official indicators')).toBeInTheDocument();
  expect(
    screen.getByText(/not enough published observations for a country readout/),
  ).toBeInTheDocument();
  expect(screen.getByText(/Read the stated unit/)).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: /Unemployment/ }));
  expect(
    screen.getByText(/No published observations are available for this series/),
  ).toBeInTheDocument();
});

it('handles empty country data and an omitted provider publication date', () => {
  const { rerender } = render(
    <CountryEconomy region={{ id: 'GB', name: 'United Kingdom', series: [] }} />,
  );
  expect(screen.getByText('0/0')).toBeInTheDocument();
  expect(screen.getByText('No observation period available')).toBeInTheDocument();
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  rerender(
    <CountryEconomy
      region={{ ...extended, series: [{ ...economySeries, source_updated_at: null }] }}
    />,
  );
  expect(screen.queryByText('Provider publication')).not.toBeInTheDocument();
});

it('does not connect a missing year in miniature histories or produce invalid constant lines', () => {
  const { container, rerender } = render(
    <IndicatorSparkline
      series={{
        ...economySeries,
        points: [
          { date: '2022', value: 4 },
          { date: '2024', value: 4 },
          { date: '2025', value: 4 },
        ],
      }}
    />,
  );
  const path = container.querySelector('path')?.getAttribute('d');
  expect(path?.match(/M/g)).toHaveLength(2);
  expect(path?.match(/L/g)).toHaveLength(1);
  expect(path).not.toMatch(/NaN|Infinity/);
  rerender(
    <IndicatorSparkline series={{ ...economySeries, points: [{ date: '2025', value: 3 }] }} />,
  );
  expect(container.querySelector('circle')).toHaveAttribute('cx', '3');
});
