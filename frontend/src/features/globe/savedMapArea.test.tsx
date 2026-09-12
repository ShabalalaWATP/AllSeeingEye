import { act, renderHook, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { aoi } from '@/test/fixtures.direction';
import { applySession } from '@/test/render';
import { server } from '@/test/server';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useSavedMapArea } from './useSavedMapArea';
import type { GlobeEngineHandle } from './useGlobeEngine';

function mount(id = aoi.id, countries = {}) {
  applySession('user');
  const flyTo = vi.fn();
  const engine = { flyTo } as unknown as GlobeEngineHandle;
  const hook = renderHook(() => useSavedMapArea(engine, countries, false), {
    wrapper: ({ children }) => (
      <MemoryRouter initialEntries={[`/?area=${id}`]}>{children}</MemoryRouter>
    ),
  });
  return { ...hook, flyTo };
}

it('loads a currently authorised saved area, focuses it and dismisses its outline', async () => {
  const { result, flyTo } = mount();
  await waitFor(() => expect(result.current.area?.id).toBe(aoi.id));
  expect(result.current.layers.map((layer) => layer.id)).toEqual(['saved-area-of-interest']);
  expect(flyTo).toHaveBeenCalledWith({ center: [35.5, 48.5], zoom: expect.any(Number) });
  act(() => result.current.close());
  expect(result.current.layers).toEqual([]);
  expect(result.current.id).toBeNull();
});

it('clears private geometry immediately when access changes and rejects unavailable IDs', async () => {
  const { result } = mount();
  await waitFor(() => expect(result.current.layers).toHaveLength(1));
  server.use(http.get('/api/direction/aois', () => HttpResponse.json({ items: [] })));
  act(() => invalidateWorkspaceAccess());
  expect(result.current.layers).toEqual([]);
  await waitFor(() => expect(result.current.message).toContain('no longer have access'));
});

it('focuses dateline-crossing bounds near the dateline, not Greenwich', async () => {
  server.use(
    http.get('/api/direction/aois', () =>
      HttpResponse.json({ items: [{ ...aoi, bbox: [170, -10, -170, 10] }] }),
    ),
  );
  const { result, flyTo } = mount();
  await waitFor(() => expect(result.current.layers).toHaveLength(1));
  expect(flyTo).toHaveBeenCalledWith({ center: [-180, 0], zoom: expect.any(Number) });
});

it('labels nation rectangles as approximate extents', async () => {
  server.use(
    http.get('/api/direction/aois', () =>
      HttpResponse.json({ items: [{ ...aoi, kind: 'countries', bbox: null, countries: ['GB'] }] }),
    ),
  );
  const { result } = mount(aoi.id, {
    GB: {
      iso2: 'GB',
      iso3: 'GBR',
      name: 'United Kingdom',
      bounds: [-8, 49, 2, 60],
      centroid: [-3, 54],
    },
  });
  await waitFor(() => expect(result.current.layers).toHaveLength(1));
  expect(result.current.message).toContain('not national borders');
});

it('does not render or focus incomplete saved bounds', async () => {
  server.use(
    http.get('/api/direction/aois', () =>
      HttpResponse.json({ items: [{ ...aoi, bbox: [30, 44] }] }),
    ),
  );
  const { result, flyTo } = mount();
  await waitFor(() => expect(result.current.message).toBe('Area boundaries are unavailable.'));
  expect(result.current.layers).toEqual([]);
  expect(flyTo).not.toHaveBeenCalled();
});
