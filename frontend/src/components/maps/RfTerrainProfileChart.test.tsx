import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { evaluateRfTerrainProfile } from '@/lib/map/rfTerrainProfile';
import { DEFAULT_RF_INPUTS } from '@/lib/map/rfPlanning';
import { RF_STATUS_CSS } from '@/lib/map/rfTerrainPresentation';
import { RfTerrainProfileChart } from './RfTerrainProfileChart';

function profile(elevations: (number | null)[], height = 100) {
  return evaluateRfTerrainProfile(
    { ...DEFAULT_RF_INPUTS, transmitHeightM: height, receiveHeightM: height },
    [
      [0, 0],
      [0.005, 0],
      [0.01, 0],
      [0.015, 0],
    ],
    [0, 500, 1000, 1500],
    elevations,
  );
}

it('shows where the direct ray first encounters terrain and keeps its downstream colour blocked', () => {
  const { container } = render(<RfTerrainProfileChart profile={profile([0, 150, 0, 0])} />);
  expect(screen.getByRole('img', { name: /Terrain profile/ })).toBeVisible();
  expect(screen.getByText(/First sampled obstruction at 0.50 km from TX/)).toBeVisible();
  expect(screen.getByText(/not zero reception/)).toBeVisible();
  const lines = container.querySelectorAll('[data-ray-status]');
  expect([...lines].map((line) => line.getAttribute('data-ray-status'))).toEqual([
    'risk',
    'blocked',
    'blocked',
  ]);
  expect(lines[2]).toHaveAttribute('stroke', RF_STATUS_CSS.blocked);
});

it('identifies Fresnel risk without falsely calling it a terrain obstruction', () => {
  render(<RfTerrainProfileChart profile={profile([0, 0, 0, 0], 5)} />);
  expect(screen.getByText(/First sampled Fresnel intrusion/)).toBeVisible();
  expect(screen.queryByText(/First sampled obstruction/)).not.toBeInTheDocument();
});

it('keeps a clear chart unmarked and refuses missing elevations', () => {
  const { rerender, container } = render(<RfTerrainProfileChart profile={profile([0, 0, 0, 0])} />);
  expect(container.querySelectorAll('[data-ray-status="clear"]')).toHaveLength(3);
  expect(screen.queryByText(/First sampled/)).not.toBeInTheDocument();
  rerender(<RfTerrainProfileChart profile={profile([0, null, 0, 0])} />);
  expect(screen.getByText(/missing elevations/)).toBeVisible();
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
});
