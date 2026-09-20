import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { TerrainAnalysisPanel } from './TerrainAnalysisPanel';
import { useTerrainAnalysis } from './useTerrainAnalysis';
import { fetchTerrainElevations } from '@/lib/api/terrain';

vi.mock('@/lib/api/terrain', () => ({ fetchTerrainElevations: vi.fn() }));
const fetch = vi.mocked(fetchTerrainElevations);
function Fixture() {
  const study = useTerrainAnalysis();
  return (
    <TerrainAnalysisPanel
      points={[
        [0, 51],
        [0.01, 51],
      ]}
      study={study}
    />
  );
}
beforeEach(() => {
  fetch.mockReset();
  fetch.mockImplementation((positions) =>
    Promise.resolve({
      elevations_m: positions.map((_, index) => 100 + index),
      zoom: 10,
      resolution_m: 90,
      provider: 'Mapzen Terrain Tiles',
      attribution: 'Fixture elevation source',
      attribution_url: 'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
      limitations: 'Fixture only',
    }),
  );
});

it('reuses drawing coordinates only on request, then exposes an inspectable ground profile', async () => {
  render(<Fixture />);
  expect(fetch).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: /Use first two points/ }));
  expect(screen.getByLabelText('Start / observer latitude')).toHaveValue('51');
  fireEvent.click(screen.getByRole('button', { name: 'Analyse terrain' }));
  expect(
    await screen.findByRole('img', { name: 'Sampled ground elevation profile' }),
  ).toBeVisible();
  expect(screen.getByRole('link', { name: 'Terrain attribution' })).toHaveAttribute(
    'href',
    'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
  );
  fireEvent.change(screen.getByLabelText('Inspect sample'), { target: { value: '2' } });
  expect(screen.getByText(/102.0 m source elevation/)).toBeVisible();
  fireEvent.change(screen.getByLabelText('End longitude'), { target: { value: '0.02' } });
  expect(
    screen.queryByRole('img', { name: 'Sampled ground elevation profile' }),
  ).not.toBeInTheDocument();
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('keeps ground visibility separate from radio coverage and rejects blank sites', async () => {
  render(<Fixture />);
  fireEvent.click(screen.getByRole('button', { name: 'Analyse terrain' }));
  expect(screen.getByRole('alert')).toHaveTextContent('Enter longitude');
  expect(fetch).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText('Analysis'), { target: { value: 'visibility' } });
  fireEvent.click(screen.getByRole('button', { name: /Use first point/ }));
  fireEvent.change(screen.getByLabelText('Observer height above ground (m)'), {
    target: { value: '5' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Analyse terrain' }));
  expect(await screen.findByText(/Marked ground samples/)).toBeVisible();
  expect(screen.getByText(/not a radio coverage prediction/)).toBeVisible();
  expect(fetch.mock.calls[0]?.[0]).toHaveLength(409);
  fireEvent.click(screen.getByRole('button', { name: 'Clear result' }));
  await waitFor(() => expect(screen.queryByText(/Marked ground samples/)).not.toBeInTheDocument());
});
