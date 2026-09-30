import { render, screen, within } from '@testing-library/react';
import { expect, it } from 'vitest';

import type { ClaimedLosses, UkraineBoard } from '@/lib/api/ukraine';
import { controlSummary, ukraineBoard } from '@/test/fixtures.ukraine';
import { FiguresStrip } from './FiguresStrip';

const claim: ClaimedLosses = {
  reported_on: '2026-09-30',
  day: 1680,
  source_url: null,
  totals: { experimental: 1234 },
  increase: {},
};

const board: UkraineBoard = {
  ...ukraineBoard,
  claims: [claim],
  categories: {},
  headline_categories: ['experimental', 'absent'],
  control: null,
  confirmed: null,
  civilian_harm: null,
};

it('shows an honest empty state without inventing totals or a claim table', () => {
  render(<FiguresStrip board={{ ...board, claims: [] }} />);
  expect(screen.getByText('No claim has been collected yet.')).toBeVisible();
  expect(
    within(screen.getByRole('list', { name: 'Headline figures' })).queryByRole('listitem'),
  ).not.toBeInTheDocument();
  expect(screen.queryByText('All claimed categories as a table')).not.toBeInTheDocument();
  expect(screen.queryByRole('link', { name: 'Original post' })).not.toBeInTheDocument();
});

it('retains unfamiliar categories, omits absent totals and defaults missing daily counts to zero', () => {
  render(
    <FiguresStrip board={{ ...board, claims: [{ ...claim, totals: {}, increase: {} }, claim] }} />,
  );
  const items = within(screen.getByRole('list', { name: 'Headline figures' })).getAllByRole(
    'listitem',
  );
  expect(items).toHaveLength(1);
  expect(within(items[0]!).getByText('experimental')).toBeVisible();
  expect(within(items[0]!).getByText('1,234')).toBeVisible();
  expect(within(items[0]!).getByText('+0 claimed on 2026-09-30')).toBeVisible();
  expect(screen.getByRole('img', { name: 'Daily claimed experimental' })).toBeInTheDocument();
  expect(screen.queryByRole('link', { name: 'Original post' })).not.toBeInTheDocument();
  const table = screen.getByRole('table', { hidden: true });
  expect(within(table).getByText('experimental')).toBeInTheDocument();
  expect(within(table).getByText('0')).toBeInTheDocument();
});

it('uses provided labels and totals while distinguishing missing control counts from a missing feed', () => {
  render(
    <FiguresStrip
      board={{
        ...board,
        categories: { experimental: 'Experimental systems' },
        claims: [
          { ...claim, source_url: 'https://example.com/original', increase: { experimental: 12 } },
        ],
        control: { ...controlSummary!, counts: {}, changes: [] },
      }}
    />,
  );
  const items = within(screen.getByRole('list', { name: 'Headline figures' })).getAllByRole(
    'listitem',
  );
  expect(items).toHaveLength(2);
  expect(within(items[0]!).getByText('Experimental systems')).toBeVisible();
  expect(within(items[0]!).getByText('+12 claimed on 2026-09-30')).toBeVisible();
  expect(within(items[1]!).getByText('0')).toBeVisible();
  expect(within(items[1]!).getByText('0 contested · 0 status changes in 30 days')).toBeVisible();
  expect(screen.getByRole('link', { name: 'Original post' })).toHaveAttribute(
    'href',
    'https://example.com/original',
  );
});

it('keeps reported control, claimed, photographed and documented figures labelled separately', () => {
  render(<FiguresStrip board={ukraineBoard} />);
  const figures = within(screen.getByRole('list', { name: 'Headline figures' }));
  expect(figures.getByText('5,892')).toBeVisible();
  expect(figures.getByText('52 contested · 1 status changes in 30 days')).toBeVisible();
  expect(figures.getAllByText('Claimed').length).toBeGreaterThan(0);
  expect(figures.getByText('Reported')).toBeVisible();
  expect(figures.getAllByText('Visually confirmed')).toHaveLength(2);
  expect(figures.getByText('Documented')).toBeVisible();
});
