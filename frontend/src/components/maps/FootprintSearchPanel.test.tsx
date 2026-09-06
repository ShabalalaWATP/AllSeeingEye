import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { searchFootprints, type FootprintCollection } from '@/lib/api/footprints';
import { FootprintSearchPanel } from './FootprintSearchPanel';

vi.mock('@/lib/api/footprints', () => ({ searchFootprints: vi.fn() }));
const empty: FootprintCollection = {
  type: 'FeatureCollection',
  status: 'empty',
  features: [],
  truncated: false,
  limitations: 'Metadata only',
  queried_at: '2026-09-06',
};
beforeEach(() => vi.clearAllMocks());
function setup() {
  const changed = vi.fn();
  const view = render(<FootprintSearchPanel onChange={changed} />);
  fireEvent.click(screen.getByText('Copernicus acquisition footprints'));
  for (const [label, value] of [
    ['West bound', '1'],
    ['South bound', '1'],
    ['East bound', '2'],
    ['North bound', '2'],
    ['Acquisition from (UTC)', '2026-09-01'],
    ['Acquisition until (UTC, exclusive)', '2026-09-03'],
  ])
    fireEvent.change(screen.getByLabelText(label!), { target: { value } });
  fireEvent.click(screen.getByLabelText(/Send this area/));
  return { ...view, changed };
}
const submit = () =>
  fireEvent.submit(screen.getByRole('form', { name: 'Search acquisition footprints' }));
it.each(['empty', 'unavailable'] as const)(
  'discloses %s without inventing coverage',
  async (status) => {
    vi.mocked(searchFootprints).mockResolvedValue({ ...empty, status });
    setup();
    submit();
    expect(
      await screen.findByText(
        status === 'empty'
          ? 'No catalogue entries returned for this query.'
          : 'Catalogue unavailable. No conclusion about coverage can be drawn.',
      ),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByText('Clear footprint results'));
    expect(screen.queryByText('Metadata only')).not.toBeInTheDocument();
  },
);
it.each([
  ['West bound', ''],
  ['West bound', '-181'],
  ['East bound', '181'],
  ['South bound', '-91'],
  ['North bound', '91'],
  ['West bound', '3'],
  ['South bound', '3'],
  ['East bound', '20'],
  ['North bound', '20'],
  ['Acquisition from (UTC)', ''],
  ['Acquisition until (UTC, exclusive)', ''],
  ['Acquisition until (UTC, exclusive)', '2026-08-01'],
  ['Acquisition until (UTC, exclusive)', '2026-10-01'],
])('rejects invalid %s %s before disclosure', (label, value) => {
  setup();
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
  submit();
  expect(screen.getByRole('alert')).toHaveTextContent('Confirm disclosure');
  expect(searchFootprints).not.toHaveBeenCalled();
});
it('requires disclosure and reports request errors', async () => {
  setup();
  fireEvent.click(screen.getByLabelText(/Send this area/));
  submit();
  expect(searchFootprints).not.toHaveBeenCalled();
  fireEvent.click(screen.getByLabelText(/Send this area/));
  vi.mocked(searchFootprints).mockRejectedValue(new Error('offline'));
  submit();
  expect(await screen.findByRole('alert')).toBeInTheDocument();
});
it.each(['cancel', 'unmount'])('discards late results after %s', async (mode) => {
  let resolve!: (value: FootprintCollection) => void;
  vi.mocked(searchFootprints).mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  const view = setup();
  submit();
  const signal = vi.mocked(searchFootprints).mock.calls[0]![1];
  if (mode === 'cancel') fireEvent.click(screen.getByText('Cancel footprint search'));
  else view.unmount();
  expect(signal.aborted).toBe(true);
  await act(async () => {
    resolve(empty);
    await Promise.resolve();
  });
  expect(view.changed).toHaveBeenCalledTimes(1);
});
it('keeps metadata for invalid geometry and permits toggling valid outlines', async () => {
  const feature: FootprintCollection['features'][number] = {
    type: 'Feature',
    id: 'scene',
    geometry: {
      type: 'MultiPolygon',
      coordinates: [
        [
          [
            [1, 1],
            [2, 1],
            [2, 2],
            [1, 1],
          ],
        ],
      ],
    },
    properties: {
      collection: 'sentinel',
      captured_at: '2026-09-01',
      cloud_cover: null,
      source_url: 'https://example.test/scene',
      licence: 'Open metadata',
      licence_url: 'https://example.test/licence',
    },
  };
  vi.mocked(searchFootprints).mockResolvedValue({
    ...empty,
    status: 'completed',
    truncated: true,
    features: [
      feature,
      {
        ...feature,
        id: 'bad',
        geometry: { type: 'MultiPolygon', coordinates: [] },
        properties: { ...feature.properties, cloud_cover: 20, source_url: 'javascript:bad' },
      },
    ],
  });
  const view = setup();
  submit();
  await screen.findByText('scene');
  expect(screen.getByText(/cannot be safely displayed/)).toBeInTheDocument();
  expect(screen.getByText(/Results are truncated/)).toBeInTheDocument();
  const toggle = screen.getByLabelText('Show purple footprint outlines');
  fireEvent.click(toggle);
  expect(view.changed).toHaveBeenLastCalledWith(null);
  fireEvent.click(toggle);
  await waitFor(() =>
    expect(view.changed).toHaveBeenLastCalledWith(
      expect.objectContaining({ type: 'FeatureCollection' }),
    ),
  );
  expect(screen.getAllByRole('link')).toHaveLength(1);
});
