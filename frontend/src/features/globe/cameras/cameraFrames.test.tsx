import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import type { Camera } from '@/lib/api/cameras';
import { CameraInspector } from './CameraInspector';
import { CameraSources } from './CameraSources';
import { loadCameraFrame, releaseCameraFrame } from './cameraFrames';

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

const relayed: Camera = {
  ...camera,
  id: 'traffic-scotland:16',
  provider: 'traffic-scotland',
  title: 'M8 Kingston Br',
  snapshot_url: '/api/cameras/frames/traffic-scotland/16.jpg',
  source_url: 'https://www.traffic.gov.scot/traffic-cameras',
};

function stubObjectUrls() {
  if (!('createObjectURL' in URL)) {
    Object.assign(URL, { createObjectURL: () => 'blob:frame', revokeObjectURL: () => undefined });
  }
}

it('loads a relayed frame through the session and releases superseded blobs', async () => {
  stubObjectUrls();
  const revoke = vi.spyOn(URL, 'revokeObjectURL');
  let calls = 0;
  server.use(
    http.get('/api/cameras/frames/traffic-scotland/16.jpg', async ({ request }) => {
      calls++;
      expect(new URL(request.url).searchParams.get('_ase_refresh')).toMatch(/^\d+-\d+$/);
      if (calls === 1) {
        await new Promise((resolve) => setTimeout(resolve, 30));
        return HttpResponse.arrayBuffer(new ArrayBuffer(0), { status: 503 });
      }
      if (calls === 2) await new Promise((resolve) => setTimeout(resolve, 30));
      return HttpResponse.arrayBuffer(new Uint8Array([255, 216, 255]).buffer, {
        headers: { 'Content-Type': 'image/jpeg' },
      });
    }),
  );
  render(<CameraInspector camera={relayed} onClose={vi.fn()} />);
  expect(screen.getByText(/Snapshot available/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Load image' }));
  expect(screen.getByRole('status')).toHaveTextContent('Loading image');
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  // A refresh before the first answer supersedes it: the late error is ignored and the
  // superseded blob, if any, is released rather than shown.
  fireEvent.click(screen.getByRole('button', { name: 'Refresh image' }));
  fireEvent.click(screen.getByRole('button', { name: 'Refresh image' }));
  const image = await screen.findByRole('img');
  expect(image.getAttribute('src')).toMatch(/^blob:/);
  await waitFor(() => expect(calls).toBe(3));
  await waitFor(() => expect(revoke).toHaveBeenCalledWith(expect.stringMatching(/^blob:/)));
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  fireEvent.load(image);
  expect(screen.getByText(/Image received/)).toBeInTheDocument();
});

it('reports a relayed frame the server refuses', async () => {
  stubObjectUrls();
  server.use(
    http.get('/api/cameras/frames/traffic-scotland/16.jpg', () =>
      HttpResponse.text('down', { status: 503 }),
    ),
  );
  render(<CameraInspector camera={relayed} onClose={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Load image' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Image unavailable');
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  releaseCameraFrame(null);
  releaseCameraFrame('https://example.test/not-a-blob');
  const fetcher = vi.fn((_path: string) => Promise.resolve(new Blob(['x'])));
  await expect(
    loadCameraFrame('/api/cameras/frames/traffic-scotland/16.jpg', 4, { fetcher }),
  ).resolves.toMatch(/^blob:/);
  expect(fetcher.mock.calls[0]?.[0]).toMatch(
    /^\/api\/cameras\/frames\/traffic-scotland\/16\.jpg\?_ase_refresh=\d+-4$/,
  );
});

it('never keeps a relayed frame blob that arrives after the inspector closes', async () => {
  stubObjectUrls();
  const created: string[] = [];
  const create = vi.spyOn(URL, 'createObjectURL').mockImplementation(() => {
    const url = `blob:late-${created.length}`;
    created.push(url);
    return url;
  });
  const revoke = vi.spyOn(URL, 'revokeObjectURL');
  let served = false;
  server.use(
    http.get('/api/cameras/frames/traffic-scotland/16.jpg', async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
      served = true;
      return HttpResponse.arrayBuffer(new Uint8Array([255, 216, 255]).buffer, {
        headers: { 'Content-Type': 'image/jpeg' },
      });
    }),
  );
  const { unmount } = render(<CameraInspector camera={relayed} onClose={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Load image' }));
  unmount();
  await new Promise((resolve) => setTimeout(resolve, 120));
  expect(served).toBe(true);
  for (const url of created) expect(revoke).toHaveBeenCalledWith(url);
  create.mockRestore();
  revoke.mockRestore();
});

it('groups the new British, Baltic, Russian and eastern providers under their regions', () => {
  const providers = [
    'traffic-scotland',
    'durham',
    'uk-live',
    'estonia',
    'tallinn',
    'baltic-live',
    'russia-live',
    'israel-live',
    'iraq-iran-live',
    'china-live',
  ].map((id) => ({
    id,
    name: id,
    status: 'available' as const,
    count: 1,
    fetched_at: null,
    message: null,
  }));
  const state = {
    catalogue: { cameras: [], providers, fetched_at: '2026-09-14T00:00:00Z' },
    providers: {},
    loading: false,
  } as unknown as Parameters<typeof CameraSources>[0]['cameras'];
  render(<CameraSources cameras={state} />);
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'karbala' } });
  expect(screen.getByText('iraq-iran-live')).toBeInTheDocument();
  expect(screen.queryByText('traffic-scotland')).not.toBeInTheDocument();
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'scotland' } });
  expect(screen.getByText('traffic-scotland')).toBeInTheDocument();
  expect(screen.getByText('uk-live')).toBeInTheDocument();
  expect(screen.queryByText('Other')).not.toBeInTheDocument();
});
