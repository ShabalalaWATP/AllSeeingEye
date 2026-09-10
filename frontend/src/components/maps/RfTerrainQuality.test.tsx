import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import type { RfAnalysis } from '@/lib/map/rfAnalysis';
import { analyseRfTerrain } from '@/lib/map/rfTerrainAnalysis';
import { createRfTerrainPath, createRfTerrainRadials } from '@/lib/map/rfTerrainSampling';
import { DEFAULT_RF_INPUTS } from '@/lib/map/rfPlanning';
import { RfTerrainQuality } from './RfTerrainQuality';

function analysis(radial: boolean): Extract<RfAnalysis, { kind: 'terrain' }> {
  const plan = radial
    ? createRfTerrainRadials([0, 0], 50)
    : createRfTerrainPath([0, 0], [0.01, 0], 3);
  const heights = plan.positions.map(() => 0);
  return {
    kind: 'terrain',
    plan,
    input: DEFAULT_RF_INPUTS,
    terrain: analyseRfTerrain(DEFAULT_RF_INPUTS, plan, heights),
    elevations: {
      elevations_m: heights,
      zoom: 10,
      resolution_m: 100,
      provider: 'Mapzen Terrain Tiles',
      attribution: 'Test credits',
      attribution_url: 'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
      limitations: 'Test terrain limits',
    },
  };
}

it('separates real sample gaps from DEM grid spacing and shows the first radial target', () => {
  render(<RfTerrainQuality analysis={analysis(true)} />);
  expect(screen.getByText('Largest sample gap').parentElement).toHaveTextContent('5,709.3 m');
  expect(screen.getByText('Nominal DEM grid spacing').parentElement).toHaveTextContent('100 m');
  expect(screen.getByText(/First assessed receiver/)).toHaveTextContent('692 m from TX');
  expect(screen.getByText(/Grid spacing is not height accuracy/)).toBeVisible();
  expect(screen.getByText(/Sample gaps exceed the terrain grid spacing/)).toBeVisible();
});

it('keeps missing samples and possible bathymetry visible without opening source details', () => {
  const result = analysis(false);
  result.terrain = analyseRfTerrain(DEFAULT_RF_INPUTS, result.plan, [-10, null, -10]);
  render(<RfTerrainQuality analysis={result} />);
  expect(screen.getByText(/1 missing terrain samples/)).toHaveTextContent(
    'Affected paths are unknown',
  );
  expect(screen.getByText(/Negative elevations may include bathymetry/)).toBeVisible();
  expect(screen.queryByText(/First assessed receiver/)).not.toBeInTheDocument();
});

it('does not invent sampling gaps or missing-data warnings for a compact complete path', () => {
  const result = analysis(false);
  result.plan = createRfTerrainPath([0, 0], [0.001, 0]);
  result.elevations.elevations_m = result.plan.positions.map(() => 0);
  result.terrain = analyseRfTerrain(DEFAULT_RF_INPUTS, result.plan, result.elevations.elevations_m);
  render(<RfTerrainQuality analysis={result} />);
  expect(screen.queryByText(/Sample gaps exceed/)).not.toBeInTheDocument();
  expect(screen.queryByText(/missing terrain samples/)).not.toBeInTheDocument();
  expect(screen.queryByText(/bathymetry/)).not.toBeInTheDocument();
});
