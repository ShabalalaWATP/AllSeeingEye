import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { expect, it } from 'vitest';

import { ukraineReference } from '@/test/fixtures.ukraineReference';

import { ForceSidePanel } from './ForceSidePanel';
import type { ChartLayout } from './ForceChart';

function panel(layout: ChartLayout = 'chart') {
  render(
    <MemoryRouter>
      <ForceSidePanel side="ru" reference={ukraineReference} layout={layout} />
    </MemoryRouter>,
  );
  return screen.getByRole('region', { name: 'Russia force structure' });
}

it('collapses and expands a branch without losing the rest of the chain', async () => {
  const user = userEvent.setup();
  const region = panel();
  const chart = within(region).getByRole('list', { name: 'Russia chain of command' });
  const subordinate = 'General Staff and Joint Grouping of Forces';
  expect(within(chart).getByText(subordinate)).toBeVisible();

  await user.click(
    within(chart).getByRole('button', {
      name: 'Collapse Supreme Commander-in-Chief, 1 direct subordinate',
    }),
  );
  expect(within(chart).getByText(subordinate)).not.toBeVisible();
  expect(within(chart).getByText('Supreme Commander-in-Chief')).toBeVisible();

  await user.click(
    within(chart).getByRole('button', {
      name: 'Expand Supreme Commander-in-Chief, 1 direct subordinate',
    }),
  );
  expect(within(chart).getByText(subordinate)).toBeVisible();
});

it('reads a chosen formation into the detail panel with its chain of command', async () => {
  const user = userEvent.setup();
  const region = panel();
  const detail = within(region).getByRole('complementary', { name: 'Russia formation detail' });
  expect(detail).toHaveTextContent('Choose a box in the chart');

  await user.click(within(region).getByRole('button', { name: /^Supreme Commander-in-Chief/ }));
  expect(detail).toHaveTextContent('Commander (reported): Vladimir Putin');
  expect(within(detail).getByRole('link', { name: 'figure record' })).toHaveAttribute(
    'href',
    '/trackers/figures',
  );
  expect(within(detail).getByRole('navigation', { name: 'Chain of command' })).toBeVisible();
});

it('offers the same structure stacked on narrow screens', () => {
  const region = panel('stacked');
  const chart = within(region).getByRole('list', { name: 'Russia chain of command' });
  expect(within(chart).getByText('Grouping North')).toBeInTheDocument();
});
