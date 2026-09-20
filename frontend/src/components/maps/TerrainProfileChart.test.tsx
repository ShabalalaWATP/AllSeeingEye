import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { TerrainProfileChart } from './TerrainProfileChart';
import { analyseTerrainStudy } from '@/lib/map/terrainAnalysis';
import { createRfTerrainPath } from '@/lib/map/rfTerrainSampling';
import type { TerrainElevations } from '@/lib/api/terrain';

function profile(elevations_m: number[]) {
  const input = {
    mode: 'profile' as const,
    origin: [0, 51] as [number, number],
    end: [0.001, 51] as [number, number],
    radiusKm: 1,
    observerHeightM: 2,
  };
  const provenance: TerrainElevations = {
    elevations_m,
    zoom: 10,
    resolution_m: 90,
    provider: 'Mapzen Terrain Tiles',
    attribution: 'Fixture',
    attribution_url: 'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
    limitations: 'Fixture only',
  };
  return analyseTerrainStudy(
    input,
    createRfTerrainPath(input.origin, input.end, elevations_m.length),
    provenance,
  );
}

it('breaks the displayed profile across unknown samples without drawing flat replacements', () => {
  const highlight = vi.fn();
  const { container } = render(
    <TerrainProfileChart
      study={profile([10, NaN, 30, 40, 50])}
      highlighted={1}
      onHighlight={highlight}
    />,
  );
  expect(screen.getByText(/Unknown elevation/)).toBeVisible();
  const segments = container.querySelectorAll('polyline');
  expect(segments).toHaveLength(2);
  expect(segments[0]?.getAttribute('points')?.split(' ')).toHaveLength(1);
  expect(segments[1]?.getAttribute('points')?.split(' ')).toHaveLength(3);
  fireEvent.change(screen.getByLabelText('Inspect sample'), { target: { value: '4' } });
  expect(highlight).toHaveBeenCalledWith(4);
});

it('renders fully unknown terrain without inventing a numerical height range', () => {
  const { container } = render(
    <TerrainProfileChart study={profile([NaN, NaN, NaN])} highlighted={0} onHighlight={vi.fn()} />,
  );
  expect(screen.getByRole('img', { name: 'Sampled ground elevation profile' })).toBeVisible();
  expect(screen.getByText(/Unknown elevation/)).toBeVisible();
  expect(
    [...container.querySelectorAll('polyline')].every((line) => line.getAttribute('points') === ''),
  ).toBe(true);
  expect(container.querySelector('svg')?.innerHTML).not.toContain('NaN');
});
