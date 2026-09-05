import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderApp } from '@/test/render';

describe('maritime, space and cyber trackers', () => {
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

  it('shows outages, ransomware and exploited vulnerabilities', async () => {
    renderApp('/trackers/cyber', 'user');
    expect(
      await screen.findByRole('heading', { name: 'Cyber' }, { timeout: 5000 }),
    ).toBeInTheDocument();
    const outages = await screen.findByRole('list', { name: 'Outages by nation' });
    expect(within(outages).getByText('TN')).toBeInTheDocument();
    const groups = screen.getByRole('list', { name: 'Ransomware by group' });
    expect(within(groups).getByText('akira')).toBeInTheDocument();
    const kev = screen.getByRole('region', { name: 'Known exploited vulnerabilities' });
    expect(within(kev).getByText(/CVE-2026-0001/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Generate report' })).toHaveAttribute(
      'href',
      '/reports?template=cyber_summary',
    );
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
    expect(within(nav).getByRole('link', { name: /Cyber/ })).toHaveAttribute(
      'href',
      '/trackers/cyber',
    );
    expect(within(nav).getByRole('link', { name: /Aviation/ })).toHaveAttribute(
      'href',
      '/trackers/aviation',
    );
  });
});
