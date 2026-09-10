import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { RfMapReadout } from './RfMapReadout';
import type { RfAnalysis } from '@/lib/map/rfAnalysis';
import { rfMapEstimate } from '@/lib/map/rfMap';
import { DEFAULT_RF_INPUTS } from '@/lib/map/rfPlanning';
import { createRfTerrainPath } from '@/lib/map/rfTerrainSampling';
import { analyseRfTerrain } from '@/lib/map/rfTerrainAnalysis';

it('keeps the map clear before a result exists and exposes the reference key on demand', () => {
  const { container, rerender } = render(<RfMapReadout analysis={null} estimate={null} />);
  expect(container).toBeEmptyDOMElement();
  rerender(<RfMapReadout analysis={null} estimate={rfMapEstimate(DEFAULT_RF_INPUTS, [0, 51])} />);
  expect(screen.getByText(/RF · Ideal limit/)).toBeVisible();
  expect(screen.getByText('Beyond ideal limit')).not.toBeVisible();
  fireEvent.click(screen.getByText(/RF · Ideal limit/));
  expect(screen.getByText('Beyond ideal limit')).toBeVisible();
  expect(screen.getByText(/Terrain has not been checked/)).toBeVisible();
});

it.each(['clear', 'blocked', 'unknown', 'radial'] as const)(
  'shows an honest compact label for %s terrain',
  (kind) => {
    const plan = createRfTerrainPath([0, 51], [0.01, 51], 3);
    const input = { ...DEFAULT_RF_INPUTS, transmitHeightM: 100, receiveHeightM: 100 };
    const terrain = analyseRfTerrain(input, plan, [
      0,
      kind === 'blocked' ? 200 : kind === 'unknown' ? null : 0,
      0,
    ]);
    if (kind === 'radial') {
      terrain.kind = 'radial';
      terrain.path = null;
      terrain.receiver = null;
    }
    const analysis: RfAnalysis = {
      kind: 'terrain',
      terrain,
      plan,
      input,
      elevations: {
        elevations_m: [0, 0, 0],
        zoom: 10,
        resolution_m: 100,
        provider: 'Mapzen Terrain Tiles',
        attribution: 'Fixture',
        attribution_url: 'https://example.com/',
        limitations: 'Fixture',
      },
    };
    render(<RfMapReadout analysis={analysis} estimate={null} />);
    expect(
      screen.getByText(
        kind === 'blocked'
          ? /Obstruction sample/
          : kind === 'clear'
            ? /sampled pass/
            : kind === 'unknown'
              ? /Receiver.*unknown/
              : /360° terrain estimate/,
      ),
    ).toBeVisible();
    expect(screen.getByText('Direct path obstructed')).toBeInTheDocument();
  },
);
