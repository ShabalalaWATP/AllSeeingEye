import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderApp } from '@/test/render';

describe('maritime and space trackers', () => {
  it('shows the maritime warnings by area and kind', async () => {
    renderApp('/trackers/maritime', 'user');
    expect(
      await screen.findByRole('heading', { name: 'Maritime' }, { timeout: 5000 }),
    ).toBeInTheDocument();
    const areas = await screen.findByRole('list', { name: 'Warnings by area' });
    expect(within(areas).getByText('4')).toBeInTheDocument();
    const notable = screen.getByRole('region', { name: 'Notable warnings' });
    expect(within(notable).getByText(/GUNNERY EXERCISE/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Generate report' })).toHaveAttribute(
      'href',
      '/reports?template=maritime_activity',
    );
  });

  it('shows stations, launches and the K index', async () => {
    renderApp('/trackers/space', 'user');
    expect(
      await screen.findByRole('heading', { name: 'Space' }, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(await screen.findByText('5.33 storm')).toBeInTheDocument();
    const stations = screen.getByRole('region', { name: 'Stations' });
    expect(within(stations).getByText('ISS (ZARYA)')).toBeInTheDocument();
    expect(within(stations).getByText(/420 km/)).toBeInTheDocument();
    const launches = screen.getByRole('region', { name: 'Launches' });
    expect(within(launches).getByText('Launch: Spectrum')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Generate report' })).not.toBeInTheDocument();
  });

  it('links to every module from the trackers page', async () => {
    renderApp('/trackers', 'user');
    const nav = await screen.findByRole('list', { name: 'Modules' }, { timeout: 5000 });
    expect(within(nav).getByRole('link', { name: /Maritime/ })).toHaveAttribute(
      'href',
      '/trackers/maritime',
    );
    expect(within(nav).getByRole('link', { name: /Space/ })).toHaveAttribute(
      'href',
      '/trackers/space',
    );
    // The cyber board lives in the cyber intelligence workspace, reached from the rail.
    expect(within(nav).queryByRole('link', { name: /Cyber/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: 'Research tools' })).not.toBeInTheDocument();
    expect(within(nav).getByRole('link', { name: /Aviation/ })).toHaveAttribute(
      'href',
      '/trackers/aviation',
    );
  });
});
