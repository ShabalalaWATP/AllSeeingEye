import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { Geodesic } from 'geographiclib-geodesic';
import type { RfAnalysis } from '@/lib/map/rfAnalysis';
import { DEFAULT_RF_INPUTS } from '@/lib/map/rfPlanning';
import { createRfTerrainPath, createRfTerrainRadials } from '@/lib/map/rfTerrainSampling';
import { analyseRfTerrain } from '@/lib/map/rfTerrainAnalysis';
import { calculateHfSkywave } from '@/lib/map/hfSkywave';
import { RfAnalysisResults } from './RfAnalysisResults';
import { RfTerrainProfileChart } from './RfTerrainProfileChart';

function terrain(radial = false): Extract<RfAnalysis, { kind: 'terrain' }> {
  const plan = radial
    ? createRfTerrainRadials([0, 51], 5)
    : createRfTerrainPath([0, 51], [0.01, 51], 3);
  const heights = plan.positions.map((_, index) => (index === 0 ? -10 : index === 1 ? 90 : 20));
  const input = { ...DEFAULT_RF_INPUTS, transmitHeightM: 5, receiveHeightM: 3 };
  return {
    kind: 'terrain',
    plan,
    input,
    terrain: analyseRfTerrain(input, plan, heights),
    elevations: {
      elevations_m: heights,
      zoom: 10,
      resolution_m: 100,
      provider: 'Mapzen Terrain Tiles',
      attribution: 'Test terrain credits',
      attribution_url: 'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
      limitations: 'Coarse source data',
    },
  };
}

it('shows source elevation separately from antenna height and an obstructed path profile', () => {
  render(<RfAnalysisResults analysis={terrain()} />);
  expect(screen.getByText('-10.0 m')).toBeVisible();
  expect(screen.getByText('-5.0 m antenna elevation')).toBeVisible();
  expect(screen.getByText('23.0 m antenna elevation')).toBeVisible();
  expect(screen.getByText('Sampled terrain blocks line of sight')).toBeVisible();
  expect(screen.getByRole('img', { name: /Terrain profile/ })).toBeVisible();
  expect(screen.getByText(/Negative elevations are retained/)).toBeInTheDocument();
});

it('shows radial survey scope and refuses to draw a profile with missing heights', () => {
  const analysis = terrain(true);
  const { unmount } = render(<RfAnalysisResults analysis={analysis} />);
  expect(screen.getByText('Sampled terrain sectors')).toBeVisible();
  expect(screen.getByText('24 bearings, 3 m receiver AGL')).toBeVisible();
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  unmount();
  const pathAnalysis = terrain();
  const missing = analyseRfTerrain(pathAnalysis.input, pathAnalysis.plan, [null, 90, 20]);
  render(<RfTerrainProfileChart profile={missing.path!} />);
  expect(screen.getByText(/missing elevations/)).toBeVisible();
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
});

it.each([3, 29])(
  'labels HF skywave as geometry, including an incompatible scenario at %s MHz',
  (frequencyMHz) => {
    const scenario = calculateHfSkywave({
      frequencyMHz,
      criticalFrequencyMHz: 5,
      virtualHeightKm: 300,
      minElevationDeg: 30,
      maxElevationDeg: 80,
    });
    render(
      <RfAnalysisResults
        analysis={{ kind: 'hf-skywave', estimate: { origin: [0, 51], frequencyMHz, scenario } }}
      />,
    );
    expect(screen.getByText('Single-hop geometry scenario')).toBeVisible();
    expect(screen.getByText(/do not predict signal strength or reception/)).toBeVisible();
    if (!scenario.compatible)
      expect(screen.getByText('No compatible hop in these assumptions')).toBeVisible();
  },
);

function groundwave(
  powers: number[],
  receiverKm?: number,
): Extract<RfAnalysis, { kind: 'hf-groundwave' }> {
  const point =
    receiverKm === undefined ? null : Geodesic.WGS84.Direct(51, 0, 90, receiverKm * 1000);
  return {
    kind: 'hf-groundwave',
    origin: [0, 51],
    receiver: point ? [point.lon2!, point.lat2!] : null,
    input: { ...DEFAULT_RF_INPUTS, frequencyMHz: 7, sensitivityDbm: -100 },
    result: {
      model: 'NTIA LFMF 1.1 (P.368-10)',
      status: 'calculated',
      source_url: 'https://github.com/NTIA/LFMF/tree/v1.1',
      limitations: 'Test homogeneous surface',
      samples: powers.map((received_power_dbm, index) => ({
        distance_km: [1, 10, 100][index]!,
        received_power_dbm,
        basic_transmission_loss_db: 100,
        native_reference_field_dbuv_m: 20,
        method: 'flat_earth',
      })),
    },
  };
}

it('keeps HF range conservative and displays an interpolated receiver only within the sample domain', () => {
  render(<RfAnalysisResults analysis={groundwave([-80, -90, -110], Math.sqrt(10))} />);
  expect(screen.getByText('Last consecutive passing sample')).toBeVisible();
  expect(screen.getByText('-85.0 dBm')).toBeVisible();
  expect(screen.getByText(/threshold crossing between samples is unresolved/)).toBeVisible();
  expect(
    screen.getByRole('img', { name: 'Modelled received power versus distance' }),
  ).toBeVisible();
});

it('does not call the study limit a maximum range or extrapolate receiver power beyond it', () => {
  render(<RfAnalysisResults analysis={groundwave([-70, -80, -90], 150)} />);
  expect(screen.getByText('Passes through sampled limit')).toBeVisible();
  expect(screen.getByText(/search limit, not a maximum range/)).toBeVisible();
  expect(screen.getByText(/Receiver is outside the sampled interval/)).toBeVisible();
  expect(screen.queryByText('Modelled receive level')).not.toBeInTheDocument();
});

it('shows no passing range when the first groundwave sample fails', () => {
  render(<RfAnalysisResults analysis={groundwave([-110, -90, -80])} />);
  expect(screen.getByText('No passing range established')).toBeVisible();
  expect(screen.getByText('Below threshold')).toBeVisible();
});
