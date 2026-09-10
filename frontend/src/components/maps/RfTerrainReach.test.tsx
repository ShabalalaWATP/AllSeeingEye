import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { RfTerrainReach } from './RfTerrainReach';
import { analyseRfTerrain } from '@/lib/map/rfTerrainAnalysis';
import { createRfTerrainPath, createRfTerrainRadials } from '@/lib/map/rfTerrainSampling';
import { DEFAULT_RF_INPUTS } from '@/lib/map/rfPlanning';
import type { RfInputs } from '@/lib/map/rfPlanning';

function path(elevations: (number | null)[], patch: Partial<RfInputs> = {}) {
  return analyseRfTerrain(
    {
      ...DEFAULT_RF_INPUTS,
      transmitHeightM: 100,
      receiveHeightM: 100,
      transmitDbm: 40,
      sensitivityDbm: -120,
      ...patch,
    },
    createRfTerrainPath([0, 0], [0.01, 0], 3),
    elevations,
  );
}

it('gives the first obstruction distance without claiming zero reception after a ridge', () => {
  render(<RfTerrainReach terrain={path([0, 200, 0])} />);
  expect(screen.getByText(/First sampled obstruction/)).toHaveTextContent('0.56 km');
  expect(screen.getByText(/Diffraction may still carry a signal/)).toBeVisible();
  expect(screen.getByText(/do not establish coverage for other receiver heights/)).toBeVisible();
});

it('separates Fresnel intrusion from weak power on a geometrically clear ray', () => {
  const { rerender } = render(
    <RfTerrainReach terrain={path([0, 0, 0], { transmitHeightM: 5, receiveHeightM: 5 })} />,
  );
  expect(screen.getByText(/First sampled Fresnel restriction/)).toBeVisible();
  expect(screen.queryByText(/First sampled obstruction/)).not.toBeInTheDocument();
  rerender(<RfTerrainReach terrain={path([0, 0, 0], { transmitDbm: -100 })} />);
  expect(screen.getByText(/below receiver sensitivity/)).toBeVisible();
  expect(screen.queryByText(/First sampled Fresnel restriction/)).not.toBeInTheDocument();
});

it('states when the full sampled link passes or terrain is unknown', () => {
  const { rerender } = render(<RfTerrainReach terrain={path([0, 0, 0])} />);
  expect(screen.getByText(/Sampled clearance passes to the receiver/)).toBeVisible();
  rerender(<RfTerrainReach terrain={path([0, null, 0])} />);
  expect(screen.getByText(/Missing terrain prevents/)).toBeVisible();
  expect(screen.queryByText(/First sampled obstruction/)).not.toBeInTheDocument();
});

it('lists last passing and first failing target distances for every surveyed bearing', () => {
  const plan = createRfTerrainRadials([0, 51], 5, 4, 4);
  const heights: (number | null)[] = plan.positions.map(() => 0);
  heights[2] = 1000;
  heights[5] = null;
  const analysis = analyseRfTerrain(
    { ...DEFAULT_RF_INPUTS, transmitHeightM: 100, receiveHeightM: 100 },
    plan,
    heights,
  );
  render(<RfTerrainReach terrain={analysis} />);
  expect(screen.getByText(/last passing target by direction/i)).toBeVisible();
  expect(screen.getAllByRole('row', { hidden: true })).toHaveLength(5);
  expect(screen.getByText('No pass')).toBeInTheDocument();
  expect(screen.getByText('Missing terrain')).toBeInTheDocument();
  expect(screen.getByText(/does not locate the obstructing ridge/)).toBeInTheDocument();
});
