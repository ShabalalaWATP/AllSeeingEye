import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { beforeAll, describe, expect, it } from 'vitest';

import { ukraineBoard, ukraineControl } from '@/test/fixtures.ukraine';
import { civilianHarm, confirmedLosses } from '@/test/fixtures.ukraineFigures';
import { applySession } from '@/test/render';

import { HarmCard, OryxCards } from './ConfirmedFigures';
import { LensSections } from './LensSections';
import { UkraineMap } from './UkraineMap';

beforeAll(() => applySession('user'));

describe('lens and figure edge cases', () => {
  it('renders lenses without series, harm or matching items', () => {
    render(
      <MemoryRouter>
        <LensSections
          board={{
            ...ukraineBoard,
            lens_series: [],
            civilian_harm: {
              ...civilianHarm,
              references: [{ ...civilianHarm.references[0]!, basis: 'unknown' }],
            },
            updates: [],
          }}
        />
      </MemoryRouter>,
    );
    expect(screen.queryByRole('img', { name: /items per day/ })).toBeNull();
    const references = screen.getByRole('list', { name: 'Casualty references' });
    expect(within(references).getByText('Reported')).toBeInTheDocument();
    expect(screen.getAllByText('No retained item matches this lens in the window.')).toHaveLength(
      3,
    );
    const { container } = render(
      <MemoryRouter>
        <LensSections board={{ ...ukraineBoard, civilian_harm: null, updates: [] }} />
      </MemoryRouter>,
    );
    expect(
      within(container).queryByRole('table', { name: /verified by the UN monitoring mission/ }),
    ).toBeNull();
  });

  it('omits the sparkline without a series and counts a null injured figure as nought', () => {
    render(
      <ul>
        <OryxCards confirmed={{ ...confirmedLosses, days: [] }} />
        <HarmCard
          harm={{
            ...civilianHarm,
            months: [{ ...civilianHarm.months[0]!, injured: null }],
          }}
        />
      </ul>,
    );
    expect(screen.queryByRole('img', { name: /cumulative confirmed losses/ })).toBeNull();
    expect(screen.getByText(/^0 injured/)).toBeInTheDocument();
  });

  it('describes a stale provider without attribution and an unavailable loss layer', async () => {
    render(
      <UkraineMap
        loaders={{
          control: () => Promise.resolve(ukraineControl),
          frontline: () =>
            Promise.resolve({
              status: 'stale',
              reason: 'Refresh failed',
              provider: null,
              attribution: null,
              terms: null,
              assessed_at: null,
              downloaded_at: null,
              features: [],
            }),
          spotted: () =>
            Promise.resolve({
              status: 'unavailable',
              reason: 'Provider unavailable',
              attribution: 'WarSpotting',
              downloaded_at: null,
              losses: [],
            }),
        }}
      />,
    );
    const note = await screen.findByRole('list', { name: 'Provider layers' });
    await screen.findByText(/provider \(stale\)/);
    expect(note).toHaveTextContent('Spotted losses: WarSpotting (unavailable, 0 markers)');
    expect(screen.getByRole('list', { name: 'Map legend' })).not.toHaveTextContent('Provider:');
  });
});
