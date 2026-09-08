import { act, renderHook, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { fetchCameras, type CameraCatalogue } from '@/lib/api/cameras';
import { useCameras } from './useCameras';

vi.mock('@/lib/api/cameras', () => ({ fetchCameras: vi.fn() }));

function catalogue(provider: string, empty = false): CameraCatalogue {
  return {
    cameras: empty
      ? []
      : [
          {
            id: provider,
            provider,
            title: provider,
            latitude: 0,
            longitude: 0,
            snapshot_url: null,
            source_url: 'https://example.com/',
            attribution: 'Provider',
            captured_at: null,
            coordinate_precision: 'exact',
          },
        ],
    providers: [
      {
        id: provider,
        name: provider,
        status: 'available',
        count: empty ? 0 : 1,
        fetched_at: null,
        message: null,
      },
    ],
    fetched_at: '2026-09-08T00:00:00Z',
  };
}

it('keeps both rapidly enabled regions and refreshes every enabled region', async () => {
  const fetch = vi.mocked(fetchCameras);
  fetch.mockImplementation((_signal, id) => Promise.resolve(catalogue(id ?? 'tfl')));
  const { result } = renderHook(useCameras);
  act(() => result.current.setEnabled(true));
  await waitFor(() => expect(result.current.loading).toBe(false));
  act(() => result.current.toggleProvider('poland'));
  act(() => result.current.toggleProvider('bulgaria'));
  await waitFor(() =>
    expect(result.current.visible.map((c) => c.provider)).toEqual(
      expect.arrayContaining(['poland', 'bulgaria']),
    ),
  );
  fetch.mockClear();
  act(() => result.current.refresh());
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(fetch.mock.calls.map((call) => call[1])).toEqual(
    expect.arrayContaining(['tfl', 'hongkong', 'fintraffic', 'poland', 'bulgaria']),
  );
});

it('retains failed providers on partial refresh and removes fulfilled empty catalogues', async () => {
  const fetch = vi.mocked(fetchCameras);
  fetch.mockImplementation((_signal, id) => Promise.resolve(catalogue(id ?? 'tfl')));
  const { result } = renderHook(useCameras);
  act(() => result.current.setEnabled(true));
  await waitFor(() => expect(result.current.loading).toBe(false));
  act(() => result.current.toggleProvider('poland'));
  await waitFor(() =>
    expect(result.current.visible.some((c) => c.provider === 'poland')).toBe(true),
  );
  fetch.mockImplementation((_signal, id) => {
    if (id === 'poland') return Promise.reject(Error('Provider unavailable'));
    return Promise.resolve(catalogue(id ?? 'tfl', true));
  });
  act(() => result.current.refresh());
  await waitFor(() => expect(result.current.error).toContain('could not be loaded'));
  expect(result.current.visible.map((c) => c.provider)).toEqual(['poland']);
});

it('reuses completed catalogues across toggles and preserves unrelated selection', async () => {
  const fetch = vi.mocked(fetchCameras);
  fetch.mockClear();
  fetch.mockImplementation((_signal, id) => Promise.resolve(catalogue(id ?? 'tfl')));
  const { result } = renderHook(useCameras);
  act(() => result.current.setEnabled(true));
  await waitFor(() => expect(result.current.loading).toBe(false));
  act(() => result.current.select(result.current.visible[0]!));
  fetch.mockClear();
  act(() => result.current.toggleProvider('poland'));
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(fetch.mock.calls.map((call) => call[1])).toEqual(['poland']);
  expect(result.current.selected?.provider).toBe('tfl');
  act(() => result.current.toggleProvider('poland'));
  act(() => result.current.toggleProvider('poland'));
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(fetch).toHaveBeenCalledTimes(1);
  act(() => result.current.toggleProvider('tfl'));
  act(() => result.current.toggleProvider('tfl'));
  expect(result.current.selected).toBeNull();
  act(() => result.current.setEnabled(false));
  act(() => result.current.setEnabled(true));
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('limits catalogue concurrency to four and refreshes each enabled provider once', async () => {
  const fetch = vi.mocked(fetchCameras);
  fetch.mockClear();
  let active = 0;
  let maximum = 0;
  const pending: (() => void)[] = [];
  fetch.mockImplementation(
    (signal, id) =>
      new Promise((resolve, reject) => {
        active++;
        maximum = Math.max(maximum, active);
        const cancel = () => {
          active--;
          reject(new Error('aborted'));
        };
        signal.addEventListener('abort', cancel, { once: true });
        pending.push(() => {
          signal.removeEventListener('abort', cancel);
          active--;
          resolve(catalogue(id ?? 'tfl'));
        });
      }),
  );
  const { result } = renderHook(useCameras);
  act(() => {
    for (let i = 0; i < 9; i++) result.current.toggleProvider(`region${i}`);
    result.current.setEnabled(true);
  });
  expect(active).toBe(4);
  while (pending.length) {
    await act(async () => {
      pending.splice(0).forEach((done) => done());
      await Promise.resolve();
    });
  }
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(maximum).toBe(4);
  expect(fetch).toHaveBeenCalledTimes(12);
  fetch.mockClear();
  act(() => result.current.refresh());
  expect(active).toBe(4);
  while (pending.length) {
    await act(async () => {
      pending.splice(0).forEach((done) => done());
      await Promise.resolve();
    });
  }
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(fetch).toHaveBeenCalledTimes(12);
  expect(maximum).toBe(4);
});

it('aborts active requests and never starts queued providers after disabling', async () => {
  const fetch = vi.mocked(fetchCameras);
  fetch.mockClear();
  fetch.mockImplementation(
    (signal) =>
      new Promise((_resolve, reject) =>
        signal.addEventListener('abort', () => reject(new Error('aborted')), { once: true }),
      ),
  );
  const { result } = renderHook(useCameras);
  act(() => {
    for (let i = 0; i < 8; i++) result.current.toggleProvider(`region${i}`);
    result.current.setEnabled(true);
  });
  expect(fetch).toHaveBeenCalledTimes(4);
  await act(async () => {
    result.current.setEnabled(false);
    await Promise.resolve();
  });
  expect(fetch.mock.calls.every((call) => call[0].aborted)).toBe(true);
  expect(fetch).toHaveBeenCalledTimes(4);
  expect(result.current.error).toBeNull();
  expect(result.current.visible).toEqual([]);
});

it('bounds retained catalogues, evicts disabled providers first and explains active overflow', async () => {
  const fetch = vi.mocked(fetchCameras);
  fetch.mockClear();
  fetch.mockImplementation((_signal, id) => {
    const value = catalogue(id ?? 'tfl');
    if (id?.startsWith('large'))
      value.cameras = Array.from({ length: 40000 }, (_, i) => ({
        ...value.cameras[0]!,
        id: `${id}:${i}`,
      }));
    return Promise.resolve(value);
  });
  const { result } = renderHook(useCameras);
  act(() => result.current.setEnabled(true));
  await waitFor(() => expect(result.current.loading).toBe(false));
  act(() => result.current.toggleProvider('large-a'));
  await waitFor(() => expect(result.current.loading).toBe(false));
  act(() => result.current.toggleProvider('large-a'));
  await waitFor(() => expect(result.current.loading).toBe(false));
  fetch.mockClear();
  act(() => result.current.toggleProvider('large-b'));
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(result.current.error).toBeNull();
  expect(result.current.catalogue!.cameras.length).toBeLessThanOrEqual(75000);
  // The disabled large-a payload was evicted, while the small enabled defaults survived.
  expect(result.current.catalogue!.cameras.some((camera) => camera.provider === 'large-a')).toBe(
    false,
  );
  act(() => result.current.toggleProvider('large-a'));
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(fetch.mock.calls.map((call) => call[1])).toEqual(['large-b', 'large-a']);
  expect(result.current.error).toContain('75,000');
  expect(result.current.catalogue!.cameras.length).toBeLessThanOrEqual(75000);
});
