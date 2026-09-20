import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderApp } from '@/test/render';

import { describeRatio } from './AviationPage';

describe('aviation tracker', () => {
  it('shows the board against baselines with emergencies first', async () => {
    renderApp('/trackers/aviation', 'user');
    expect(
      await screen.findByRole('heading', { name: 'Aviation' }, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.getByText('96')).toBeInTheDocument();
    expect(screen.getByText('1 red, 3 amber')).toBeInTheDocument();
    const emergencies = screen.getByRole('region', { name: 'Emergencies' });
    expect(
      within(emergencies).getByRole('link', {
        name: 'RCH123 (C17): squawk 7700, general emergency',
      }),
    ).toHaveAttribute('href', 'https://globe.adsb.lol/?icao=ae1234');
    const nations = screen.getByRole('table', { name: 'Military aircraft by nation' });
    const ukraine = within(nations).getByText('UA').closest('tr')!;
    expect(within(ukraine).getByText('above baseline')).toBeInTheDocument();
    const poland = within(nations).getByText('PL').closest('tr')!;
    expect(within(poland).getByText('no baseline')).toBeInTheDocument();
    const areas = screen.getByRole('table', { name: 'Watched areas' });
    expect(within(areas).getByText('Black Sea and southern Ukraine')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Generate activity report' })).toHaveAttribute(
      'href',
      '/reports?template=aviation_activity',
    );
    expect(describeRatio(0.4)).toBe('below baseline');
    expect(describeRatio(1)).toBe('steady');
  });

  it('links from the trackers page', async () => {
    renderApp('/trackers', 'user');
    const modules = await screen.findByRole('list', { name: 'Modules' }, { timeout: 5000 });
    expect(within(modules).getByRole('link', { name: 'Aviation' })).toHaveAttribute(
      'href',
      '/trackers/aviation',
    );
  });
});
