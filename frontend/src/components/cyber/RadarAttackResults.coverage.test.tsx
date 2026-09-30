import { render, screen, within } from '@testing-library/react';
import { expect, it } from 'vitest';

import type { RadarAttackSnapshot } from '@/lib/api/cyber';
import { RadarAttackResults } from './RadarAttackResults';

const snapshot: RadarAttackSnapshot = {
  status: 'ready',
  fetched_at: null,
  source_url: 'https://radar.cloudflare.com/security/application-layer',
  layers: [
    {
      layer: 'layer7',
      period_from: '2026-09-12T12:00:00Z',
      period_to: '2026-09-13T12:00:00Z',
      updated_at: null,
      unit: 'requests',
      countries: ['GB', 'FR', 'DE', 'US'].map((country_iso, index) => ({
        country_iso,
        country_name: `Country ${index + 1}`,
        rank: index + 1,
        share_percent: 25,
      })),
    },
  ],
};

it.each([
  ['disabled', 'disabled by the administrator'],
  ['not_configured', 'needs a server-side Radar Read token'],
  ['unavailable', 'attack trends are unavailable'],
] as const)('explains %s without displaying retained distributions', (status, explanation) => {
  render(<RadarAttackResults data={{ ...snapshot, status }} />);
  expect(screen.getByText(new RegExp(explanation))).toBeVisible();
  expect(screen.queryByRole('list')).not.toBeInTheDocument();
});

it.each([
  ['stale', 'Previously collected data. The latest Radar refresh failed.'],
  ['partial', 'Only one Radar attack layer is available.'],
] as const)('labels %s data while retaining its available layer', (status, explanation) => {
  render(<RadarAttackResults data={{ ...snapshot, status }} />);
  expect(screen.getByText(explanation)).toBeVisible();
  expect(within(screen.getByRole('list')).getAllByRole('listitem')).toHaveLength(4);
  expect(screen.getByText(/mitigated requests/)).toBeVisible();
  expect(screen.queryByText(/Checked/)).not.toBeInTheDocument();
});

it('limits compact summaries to three countries while preserving the layer and period', () => {
  const { rerender } = render(<RadarAttackResults data={snapshot} compact />);
  const distribution = screen.getByRole('list', { name: 'Application layer (L7) distribution' });
  expect(within(distribution).getAllByRole('listitem')).toHaveLength(3);
  expect(screen.queryByText('Country 4')).not.toBeInTheDocument();
  expect(screen.getByText(/12 Sept 2026, 12:00 to 13 Sept 2026, 12:00 UTC/)).toBeVisible();
  expect(screen.queryByRole('link', { name: 'Cloudflare Radar' })).not.toBeInTheDocument();
  rerender(<RadarAttackResults data={snapshot} />);
  expect(screen.getByText('Country 4')).toBeVisible();
  expect(screen.getByText(/not attack counts/)).toBeVisible();
  expect(screen.getByRole('link', { name: 'Cloudflare Radar' })).toHaveAttribute(
    'href',
    snapshot.source_url,
  );
});
