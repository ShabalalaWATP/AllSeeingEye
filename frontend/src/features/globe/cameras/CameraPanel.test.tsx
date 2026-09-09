import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import type { CameraState } from './useCameras';
import { CameraPanel } from './CameraPanel';
const camera = {
  id: 'tfl:1',
  provider: 'tfl',
  title: 'Bridge',
  latitude: 51,
  longitude: 0,
  snapshot_url: 'https://example.test/image.jpg',
  stream_url: null,
  stream_type: null,
  external_url: null,
  source_url: 'https://example.test',
  attribution: 'Provider',
  captured_at: null,
  coordinate_precision: 'approximate' as const,
};
function state(): CameraState {
  return {
    enabled: true,
    setEnabled: vi.fn(),
    catalogue: {
      cameras: [camera],
      providers: [
        {
          id: 'tfl',
          name: 'Transport for London',
          status: 'available',
          count: 1,
          fetched_at: null,
          message: null,
        },
      ],
      fetched_at: '2026-09-09T00:00:00Z',
    },
    loading: false,
    error: null,
    providers: { tfl: true },
    toggleProvider: vi.fn(),
    setProviderGroup: vi.fn(),
    query: '',
    setQuery: vi.fn(),
    visible: [camera],
    selected: null,
    select: vi.fn(),
    close: vi.fn(),
    refresh: vi.fn(),
  };
}
it('labels media and provider metadata without loading any preview', async () => {
  const cameras = state();
  const user = userEvent.setup();
  const { container } = render(<CameraPanel cameras={cameras} />);
  const row = screen.getByRole('button', { name: 'Bridge' });
  expect(within(row).getByText('Transport for London')).toBeVisible();
  expect(row).toHaveTextContent('Snapshot / Approximate location');
  expect(container.querySelector('img,video,iframe')).toBeNull();
  await user.click(row);
  expect(cameras.select).toHaveBeenCalledWith(camera);
});
it('keeps empty and failed catalogue recovery explicit', async () => {
  const cameras = { ...state(), visible: [], query: 'missing', error: 'Source unavailable' };
  const user = userEvent.setup();
  render(<CameraPanel cameras={cameras} />);
  expect(screen.getByRole('alert')).toHaveTextContent('Source unavailable');
  expect(screen.getByText(/No cameras match this search/)).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Refresh catalogue' }));
  expect(cameras.refresh).toHaveBeenCalledOnce();
});
it('bounds camera pages and returns to the first page when searching', async () => {
  const cameras = {
    ...state(),
    visible: Array.from({ length: 51 }, (_, index) => ({
      ...camera,
      id: String(index),
      title: `Camera ${index}`,
    })),
  };
  const user = userEvent.setup();
  render(<CameraPanel cameras={cameras} />);
  expect(screen.queryByRole('button', { name: 'Camera 50' })).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Next cameras' }));
  expect(screen.getByRole('button', { name: 'Camera 50' })).toBeVisible();
  await user.type(screen.getByLabelText('Find a camera'), 'Bridge');
  expect(screen.getByRole('button', { name: 'Camera 0' })).toBeVisible();
  expect(cameras.setQuery).toHaveBeenCalled();
});
