import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it, vi } from 'vitest';
import { renderApp } from '@/test/render';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { server } from '@/test/server';
import { areaPreview } from '@/test/areaResearchPanel';
import type { ResearchPlanInput } from '@/lib/api/researchPlan';
import { useEventsStore } from '@/stores/events';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

beforeEach(() => {
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
  useEventsStore.setState({ hidden: [] });
  server.use(http.get('/api/trackers/conflicts', () => HttpResponse.json({ items: [] })));
});

it.each(['Globe', 'Map'])(
  'draws and previews an exact research polygon in %s from the right menu',
  async (mode) => {
    const requests: ResearchPlanInput[] = [];
    server.use(
      http.post('/api/research/runs/plan', async ({ request }) => {
        const body = (await request.json()) as ResearchPlanInput;
        requests.push(body);
        return HttpResponse.json(areaPreview(body));
      }),
    );
    const { user } = renderApp('/', 'user');
    await screen.findByRole('region', { name: '3D globe' });
    await waitFor(() => expect(FakeMap.instances).toHaveLength(1));
    const map = FakeMap.instances[0]!;
    act(() => map.fire('style.load'));
    if (mode === 'Map') await user.click(screen.getByRole('button', { name: /^Map$/ }));
    await user.click(screen.getByRole('button', { name: 'Research area' }));
    expect(
      screen.getByRole('form', { name: 'Research this area' }).closest('.map-tool-panel'),
    ).toHaveAttribute('data-side', 'right');
    expect(screen.getByRole('button', { name: 'Check sources' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Draw boundary' }));
    act(() => {
      for (const [lng, lat] of [
        [0, 50],
        [1, 50],
        [0, 51],
      ])
        map.fire('click', { lngLat: { lng, lat } });
    });
    await user.click(screen.getByRole('button', { name: 'Finish boundary' }));
    await user.click(screen.getByRole('button', { name: 'Check sources' }));
    await waitFor(() => expect(requests).toHaveLength(1));
    expect(requests[0]?.research_area?.geometry).toMatchObject({
      features: [
        {
          geometry: {
            type: 'Polygon',
            coordinates: [
              [
                [0, 50],
                [1, 50],
                [0, 51],
                [0, 50],
              ],
            ],
          },
        },
      ],
    });
    expect(requests[0]?.source_ids).toBeNull();
    expect(requests[0]?.team_id).toBeNull();
    await screen.findByText('NASA FIRMS');
    await user.click(screen.getByRole('button', { name: 'Close tool' }));
    expect(screen.queryByRole('form', { name: 'Research this area' })).not.toBeInTheDocument();
    const layers = MapboxOverlay.instances[0]?.props.layers as { id: string }[];
    expect(layers.some((layer) => layer.id === 'research-area-boundary')).toBe(true);
  },
);
