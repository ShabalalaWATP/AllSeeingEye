import { act, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import {
  cameraCatalogueSchema,
  isCameraImageUrl,
  type Camera,
  type CameraCatalogue,
} from '@/lib/api/cameras';
import { useCameras } from './useCameras';
import { CameraPanel } from './CameraPanel';
import { CameraInspector } from './CameraInspector';
import { buildCameraLayers } from './cameraLayers';

const camera: Camera = {
  id: 'tfl:1',
  provider: 'tfl',
  title: 'London Bridge',
  latitude: 51.5,
  longitude: -0.1,
  snapshot_url: 'https://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/00001.00100.jpg',
  source_url: 'https://tfl.gov.uk/traffic/status/',
  attribution: 'Transport for London',
  captured_at: null,
  coordinate_precision: 'exact',
};
const catalogue: CameraCatalogue = {
  cameras: [camera, { ...camera, id: 'hk:1', title: 'Hong Kong Road', provider: 'hongkong' }],
  providers: [
    { id: 'tfl', name: 'London', status: 'available', count: 1, fetched_at: null, message: null },
  ],
  fetched_at: '2026-09-08T00:00:00Z',
};
afterEach(() => vi.useRealTimers());

it('accepts only exact official image locations and bounded valid catalogues', () => {
  for (const url of [
    camera.snapshot_url,
    'https://tdcctv.data.one.gov.hk/H001.JPG',
    'https://weathercam.digitraffic.fi/C0000101.jpg',
  ])
    expect(isCameraImageUrl(url)).toBe(true);
  for (const url of [
    'invalid',
    'http://weathercam.digitraffic.fi/C1.jpg',
    'https://weathercam.digitraffic.fi.evil.test/C1.jpg',
    'https://user:pass@weathercam.digitraffic.fi/C1.jpg',
    'https://weathercam.digitraffic.fi:123/C1.jpg',
    'https://weathercam.digitraffic.fi/C1.jpg?redirect=evil',
    'https://weathercam.digitraffic.fi/C1.jpg#x',
    'https://s3-eu-west-1.amazonaws.com/other/C1.jpg',
  ])
    expect(isCameraImageUrl(url)).toBe(false);
  expect(cameraCatalogueSchema.safeParse(catalogue).success).toBe(true);
  expect(
    cameraCatalogueSchema.safeParse({ ...catalogue, cameras: [{ ...camera, latitude: 91 }] })
      .success,
  ).toBe(false);
});

it('fetches on demand and clears selection on provider changes, search and disable', async () => {
  let calls = 0;
  server.use(
    http.get('/api/cameras', () => {
      calls++;
      return HttpResponse.json(catalogue);
    }),
  );
  const { result } = renderHook(useCameras);
  expect(calls).toBe(0);
  act(() => result.current.setEnabled(true));
  await waitFor(() => expect(result.current.visible).toHaveLength(2));
  act(() => result.current.select(camera));
  expect(result.current.selected?.id).toBe(camera.id);
  act(() => result.current.toggleProvider('tfl'));
  expect(result.current.selected).toBeNull();
  expect(result.current.visible).toHaveLength(1);
  act(() => result.current.toggleProvider('tfl'));
  act(() => result.current.setQuery('London'));
  expect(result.current.visible).toHaveLength(1);
  act(() => result.current.select(camera));
  act(() => result.current.close());
  expect(result.current.selected).toBeNull();
  await waitFor(() => expect(result.current.loading).toBe(false));
  const previousCalls = calls;
  act(() => result.current.refresh());
  await waitFor(() => expect(calls).toBeGreaterThan(previousCalls));
  act(() => result.current.setEnabled(false));
  expect(result.current.visible).toEqual([]);
});

it('reports an unavailable catalogue, retries, and ignores late responses after disabling', async () => {
  server.use(http.get('/api/cameras', () => new HttpResponse(null, { status: 503 })));
  const { result } = renderHook(useCameras);
  act(() => result.current.setEnabled(true));
  await waitFor(() => expect(result.current.error).toMatch(/could not be loaded/));
  let respond: (() => void) | undefined;
  server.use(
    http.get('/api/cameras', async () => {
      await new Promise<void>((resolve) => {
        respond = resolve;
      });
      return HttpResponse.json(catalogue);
    }),
  );
  act(() => result.current.refresh());
  await waitFor(() => expect(respond).toBeDefined());
  act(() => result.current.setEnabled(false));
  await act(async () => {
    respond?.();
    await Promise.resolve();
  });
  expect(result.current.catalogue).toBeNull();
  expect(result.current.loading).toBe(false);
});

it('does not request an image before consent, handles errors and removes expired images', () => {
  vi.useFakeTimers();
  const close = vi.fn();
  render(<CameraInspector camera={camera} onClose={close} />);
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  expect(screen.getByText(/Capture time: Unknown/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Load image' }));
  fireEvent.error(screen.getByRole('img'));
  expect(screen.getByRole('alert')).toHaveTextContent('Image unavailable');
  fireEvent.click(screen.getByRole('button', { name: 'Refresh image' }));
  fireEvent.load(screen.getByRole('img'));
  expect(screen.getByText(/Image received/)).toBeInTheDocument();
  act(() => {
    vi.advanceTimersByTime(900000);
  });
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  expect(screen.getByRole('status')).toHaveTextContent('hidden after 15 minutes');
  fireEvent.keyDown(window, { key: 'Escape' });
  expect(close).toHaveBeenCalledOnce();
});

it('blocks unsafe snapshots and resets image consent when the selected camera changes', () => {
  const { rerender } = render(
    <CameraInspector
      camera={{ ...camera, snapshot_url: 'https://evil.test/x.jpg' }}
      onClose={vi.fn()}
    />,
  );
  expect(screen.getByRole('button', { name: 'Load image' })).toBeDisabled();
  rerender(
    <CameraInspector
      camera={{ ...camera, id: 'other', captured_at: '2026-09-08T12:00:00Z' }}
      onClose={vi.fn()}
    />,
  );
  expect(screen.getByRole('button', { name: 'Load image' })).toBeEnabled();
  fireEvent.click(screen.getByRole('button', { name: 'Load image' }));
  rerender(<CameraInspector camera={camera} onClose={vi.fn()} />);
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
});

it('requests a new image URL on refresh and bounds loading without accepting late images', () => {
  vi.useFakeTimers();
  render(<CameraInspector camera={camera} onClose={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Load image' }));
  const first = screen.getByRole('img');
  const firstUrl = new URL(first.getAttribute('src')!);
  expect(firstUrl.origin + firstUrl.pathname).toBe(camera.snapshot_url);
  expect(firstUrl.searchParams.has('_ase_refresh')).toBe(true);
  fireEvent.click(screen.getByRole('button', { name: 'Refresh image' }));
  const second = screen.getByRole('img');
  expect(second.getAttribute('src')).not.toBe(first.getAttribute('src'));
  fireEvent.load(first);
  expect(screen.getByRole('status')).toHaveTextContent('Loading image');
  act(() => {
    vi.advanceTimersByTime(20_000);
  });
  expect(screen.getByRole('alert')).toHaveTextContent('Image unavailable');
  fireEvent.load(second);
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Refresh image' }));
  const third = screen.getByRole('img');
  fireEvent.load(third);
  act(() => {
    vi.advanceTimersByTime(900_000);
  });
  fireEvent.load(third);
  expect(screen.getByRole('status')).toHaveTextContent('hidden after 15 minutes');
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
});

it('browses all overlapping facilities using the paginated list and provider switches', async () => {
  server.use(
    http.get('/api/cameras', () =>
      HttpResponse.json({
        ...catalogue,
        cameras: Array.from({ length: 51 }, (_, i) => ({
          ...camera,
          id: String(i),
          title: `Road ${i}`,
        })),
      }),
    ),
  );
  const select = vi.fn();
  function Panel() {
    const cameras = useCameras();
    return <CameraPanel cameras={cameras} onSelect={select} />;
  }
  render(<Panel />);
  const user = userEvent.setup();
  await user.click(screen.getByRole('switch', { name: /Show public cameras/ }));
  await screen.findByRole('button', { name: 'Road 0' });
  await user.click(screen.getByRole('button', { name: 'Next cameras' }));
  await user.click(screen.getByRole('button', { name: 'Road 50' }));
  expect(select).toHaveBeenCalledWith(expect.objectContaining({ id: '50' }));
  await user.click(screen.getByRole('button', { name: 'Previous cameras' }));
  await user.type(screen.getByRole('textbox', { name: 'Find a camera' }), 'Road 0');
  await user.click(screen.getByRole('switch', { name: 'London' }));
  expect(screen.getByText('0 cameras shown on the map')).toBeInTheDocument();
});

it('builds clickable camera icons with a separate selection halo on both projections', () => {
  expect(buildCameraLayers([], vi.fn(), null)).toEqual([]);
  for (const globe of [false, true]) {
    const select = vi.fn();
    const layers = buildCameraLayers([camera], select, camera.id, globe);
    expect(layers.map((layer) => layer.id)).toEqual([
      'public-camera-icons',
      'selected-camera-halo',
    ]);
    const props = layers[0]!.props;
    // Exercise the real layer accessors and pick callback without a GPU in unit tests.
    const accessor = props as unknown as {
      billboard: boolean;
      getPosition: (item: Camera) => number[];
      getIcon: () => { url: string };
      getSize: (item: Camera) => number;
      onClick: (info: { object?: Camera }) => boolean;
    };
    expect(accessor.billboard).toBe(!globe);
    expect(accessor.getPosition(camera)).toEqual([-0.1, 51.5]);
    expect(accessor.getIcon().url).toMatch(/^data:image/);
    expect(accessor.getSize(camera)).toBe(30);
    expect(accessor.getSize({ ...camera, id: 'other' })).toBe(22);
    accessor.onClick({ object: camera });
    accessor.onClick({});
    expect(select).toHaveBeenCalledOnce();
    expect(buildCameraLayers([camera], select, null, globe)).toHaveLength(1);
  }
});
