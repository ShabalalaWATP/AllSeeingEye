import { act, fireEvent, screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import { mockMatchMedia, mockWebGl2 } from '@/test/env';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { liveEvent } from '@/test/fixtures';
import { openMapTool } from '@/test/mapTools';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
// Load the real route after Vitest hoists its mocks, outside the timed steps.
import '../GlobePage';

import { indexReplay, filterReplay, cursorAtStep } from './liveReplay';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

const HOUR = 3_600_000;
const newest = Date.UTC(2026, 8, 5, 0, 0);
const CLIENT_CAP = 5_000;

/** The client cap of hazards, spread back over three days, newest first like the store. */
function retainedEvents(): LiveEvent[] {
  return Array.from({ length: CLIENT_CAP }, (_, position) =>
    liveEvent({
      id: `hazard-${position}`,
      published_at: new Date(
        newest - Math.floor((position * 72 * HOUR) / CLIENT_CAP),
      ).toISOString(),
      point: { lon: -170 + (position % 340), lat: -60 + (position % 120) },
    }),
  );
}

describe('replay over the client event cap', () => {
  beforeEach(() => {
    mockMatchMedia(false);
    useEventsStore.setState({ hidden: [] });
    useGlobeStore.setState({ terminator: false, opsRoom: false });
    server.use(http.get('/api/trackers/conflicts', () => HttpResponse.json({ items: [] })));
    FakeMap.reset();
    MapboxOverlay.reset();
    FakeEventStreamClient.reset();
    mockWebGl2(true);
  });

  it('indexes and filters 5,000 events for every retained hour within budget', () => {
    const events = retainedEvents();
    const started = performance.now();
    const index = indexReplay(events);
    for (let step = 0; step <= index.steps; step += 1) {
      filterReplay(events, index, cursorAtStep(index, step));
    }
    expect(index.steps).toBe(72);
    expect(performance.now() - started).toBeLessThan(500);
  });

  it('scrubs the live map in memory, marks it as replay and returns to live', async () => {
    const { user } = renderApp('/', 'user');
    await screen.findByText('Natural hazards: 1 loaded');
    const events = retainedEvents();
    act(() => {
      useEventsStore.setState({
        byId: Object.fromEntries(events.map((event) => [event.id, event])),
        list: events,
      });
    });
    expect(await screen.findByText('Natural hazards: 5000 loaded')).toBeInTheDocument();
    await openMapTool(user, 'Event time');
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    let started = performance.now();
    await user.click(screen.getByRole('button', { name: 'Start replay' }));
    const firstStep = performance.now() - started;
    const banner = screen.getByRole('region', { name: 'Replay mode' });
    expect(within(banner).getByText('Replay, not live')).toBeVisible();
    expect(screen.getByText('Natural hazards: 1 loaded')).toBeInTheDocument();

    const slider = screen.getByRole('slider', { name: 'Replay time' });
    started = performance.now();
    for (let step = 1; step <= 24; step += 1) {
      act(() => {
        fireEvent.change(slider, { target: { value: String(step) } });
      });
    }
    const perStep = (performance.now() - started) / 24;
    // 24 of 72 hours replayed: one third of the cap, give or take the first record.
    const label = screen.getByText(/^Natural hazards: \d+ loaded$/).textContent;
    const shown = Number(/(\d+)/.exec(label)?.[1]);
    expect(shown).toBeGreaterThan(1_600);
    expect(shown).toBeLessThan(1_700);
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(firstStep).toBeLessThan(2_000);
    expect(perStep).toBeLessThan(500);

    await user.click(within(banner).getByRole('button', { name: 'Return to live' }));
    expect(screen.queryByRole('region', { name: 'Replay mode' })).not.toBeInTheDocument();
    expect(screen.getByText('Natural hazards: 5000 loaded')).toBeInTheDocument();
  });
});
