import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import type { RadarAttackSnapshot } from '@/lib/api/cyber';
import { RadarAttackResults } from './RadarAttackTrends';

const snapshot: RadarAttackSnapshot = {
  status: 'ready',
  fetched_at: '2026-09-13T12:00:00Z',
  source_url: 'https://radar.cloudflare.com/security/application-layer',
  layers: [
    {
      layer: 'layer3',
      period_from: '2026-09-12T12:00:00Z',
      period_to: '2026-09-13T12:00:00Z',
      updated_at: '2026-09-13T11:00:00Z',
      unit: 'bytes',
      countries: [
        { country_iso: 'GB', country_name: 'United Kingdom', rank: 1, share_percent: 42.5 },
      ],
    },
  ],
};

it('labels Radar percentages as provider-wide billing-country aggregates', () => {
  render(<RadarAttackResults data={snapshot} />);
  expect(screen.getByText('42.5%')).toBeVisible();
  expect(screen.getByText(/billing country/)).toBeVisible();
  expect(screen.getByText(/not attack counts/)).toBeVisible();
  expect(screen.getByRole('link', { name: 'Cloudflare Radar' })).toHaveAttribute(
    'href',
    snapshot.source_url,
  );
});

it('does not imply data is available when the token or source is absent', () => {
  render(<RadarAttackResults data={{ ...snapshot, status: 'not_configured', layers: [] }} />);
  expect(screen.getByText(/server-side Radar Read token/)).toBeVisible();
  expect(screen.queryByText('42.5%')).not.toBeInTheDocument();
});
