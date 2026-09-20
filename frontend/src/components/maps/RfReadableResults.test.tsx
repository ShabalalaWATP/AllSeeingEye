import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { DEFAULT_RF_INPUTS, calculateRf } from '@/lib/map/rfPlanning';
import { calculateHfSkywave } from '@/lib/map/hfSkywave';
import { createRfTerrainPath } from '@/lib/map/rfTerrainSampling';
import { analyseRfTerrain } from '@/lib/map/rfTerrainAnalysis';
import { RfResults } from './RfResults';
import { RfAnalysisResults } from './RfAnalysisResults';

it('puts an explanation before the figures and lets users reveal terms and calculations', async () => {
  const user = userEvent.setup();
  render(<RfResults result={calculateRf(DEFAULT_RF_INPUTS)} />);
  const summary = screen.getByRole('region', { name: 'Result explained' });
  expect(within(summary).getByRole('heading', { name: 'What to try next' })).toBeVisible();
  expect(within(summary).getByRole('heading', { name: 'Limits of this estimate' })).toBeVisible();
  expect(screen.getByText(/Estimated receive level/)).not.toBeVisible();
  const engineering = screen.getByText('Engineering details');
  await user.click(engineering);
  expect(screen.getByText(/Estimated receive level/)).toBeVisible();
  const glossary = screen.getByText('Explain the terms');
  expect(glossary).toBeVisible();
  expect(screen.getByText(/less negative value is stronger/)).not.toBeVisible();
  await user.click(glossary);
  expect(screen.getByText(/less negative value is stronger/)).toBeVisible();
  expect(screen.getByText(/not a success percentage/)).toBeVisible();
  await user.click(engineering);
  expect(screen.getByText(/Estimated receive level/)).not.toBeVisible();
  expect(summary).toBeVisible();
});

it('keeps missing terrain and the profile explanation visible without opening technical details', () => {
  const plan = createRfTerrainPath([0, 51], [0.01, 51], 3);
  const heights = [null, 90, null];
  render(
    <RfAnalysisResults
      analysis={{
        kind: 'terrain',
        input: DEFAULT_RF_INPUTS,
        plan,
        terrain: analyseRfTerrain(DEFAULT_RF_INPUTS, plan, heights),
        elevations: {
          elevations_m: [],
          zoom: 10,
          resolution_m: 100,
          provider: 'Mapzen Terrain Tiles',
          attribution: 'Test credits',
          attribution_url: 'https://example.com',
          limitations: 'Test data',
        },
      }}
    />,
  );
  expect(screen.getByRole('region', { name: 'Result explained' })).toHaveTextContent(/missing/i);
  expect(screen.getByRole('heading', { name: 'Terrain along the path' })).toBeVisible();
  expect(screen.getByText(/Read from the transmitter/)).toBeVisible();
  expect(screen.getByText('Not assessed')).toBeVisible();
  expect(screen.getByText('Modelled receive power')).not.toBeVisible();
});

it('explains skywave limits before displaying the illustrative distance', () => {
  const scenario = calculateHfSkywave({
    frequencyMHz: 3,
    criticalFrequencyMHz: 5,
    virtualHeightKm: 300,
    minElevationDeg: 30,
    maxElevationDeg: 80,
  });
  render(
    <RfAnalysisResults
      analysis={{ kind: 'hf-skywave', estimate: { origin: [0, 51], frequencyMHz: 3, scenario } }}
    />,
  );
  const summary = screen.getByRole('region', { name: 'Result explained' });
  expect(summary).toBeVisible();
  expect(summary).toHaveTextContent(/do not estimate signal strength/i);
  expect(screen.getByText('Illustrative travel distance')).toBeVisible();
  expect(screen.getByText('Single-hop geometry scenario')).not.toBeVisible();
});
