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
