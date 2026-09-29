import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { expect, it, vi } from 'vitest';

import { countries, liveEvent } from '@/test/fixtures';

import { CountryPanel } from './CountryPanel';

const NOW = Date.UTC(2026, 8, 5, 3, 0, 0);

it('announces and shows each recent record with its category, not only a coloured dot', () => {
  render(
    <CountryPanel
      country={countries[1]!}
      events={[
        liveEvent({ id: 'a', title: 'Quake near Kyiv', country_iso: 'UA' }),
        liveEvent({ id: 'b', title: 'Advisory', category: 'political', country_iso: 'UA' }),
      ]}
      selectedId={null}
      now={NOW}
      onSelect={vi.fn()}
    />,
    { wrapper: MemoryRouter },
  );
  const records = screen.getByRole('list', { name: 'Recent country records' });
  const [quake, advisory] = within(records).getAllByRole('button');
  expect(quake).toHaveAccessibleName('Quake near Kyiv Disasters · 3h ago');
  expect(advisory).toHaveAccessibleName('Advisory Political · 3h ago');
  expect(within(quake!).getByText('Disasters · 3h ago')).toBeVisible();

  const summary = screen.getAllByRole('list')[0]!;
  expect(
    within(summary)
      .getAllByRole('listitem')
      .map((item) => item.textContent),
  ).toEqual(['Disasters 1', 'Political 1']);
});
