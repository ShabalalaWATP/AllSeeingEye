/**
 * KAN-81 benchmark: the real map route, with fake MapLibre and deck.gl, under the
 * documented sustained-stream fixture (src/test/streamFixture.ts). It prints merge, React
 * and Profiler timings per scenario as audit evidence. Timings are deliberately not pass
 * thresholds; the targets (median at most 20 ms, maximum under 50 ms) apply to this
 * fixture on a developer machine, not to every device. Run it alone for stable figures:
 * npx vitest run src/features/globe/GlobePage.streamBenchmark.test.tsx
 */
import { act, render, screen, waitFor, within } from '@testing-library/react';
import { Profiler } from 'react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';

import { routes } from '@/app/router/routes';
import { STREAM_BATCH_MS } from '@/stores/events.stream';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import { mockWebGl2 } from '@/test/env';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { applySession } from '@/test/render';
import {
  FIXTURE_BATCHES,
  FIXTURE_BATCH_SIZE,
  FIXTURE_MIRROR_SIZE,
  expireMessage,
  median,
  streamEvent,
  upsertMessage,
} from '@/test/streamFixture';
import type { SseMessage } from '@/lib/sse';
// Load the real route after Vitest hoists its mocks, outside the timed batches.
import './GlobePage';

const clock = vi.hoisted(() => ({ now: Date.UTC(2026, 8, 6) }));
vi.mock('@/lib/hooks/useNow', () => ({ useNow: () => clock.now }));
vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

afterEach(() => {
  vi.useRealTimers();
});

interface Sample {
  mergeMs: number;
  reactMs: number;
  profilerMs: number;
  commits: number;
}

function round(value: number): number {
  return Number(value.toFixed(2));
}

function summary(samples: readonly Sample[]) {
  const totals = samples.map((sample) => sample.mergeMs + sample.reactMs);
  return {
    totalMedianMs: round(median(totals)),
    totalMaxMs: round(Math.max(...totals)),
    mergeMedianMs: round(median(samples.map((sample) => sample.mergeMs))),
    reactMedianMs: round(median(samples.map((sample) => sample.reactMs))),
    profilerMedianMs: round(median(samples.map((sample) => sample.profilerMs))),
    commitsPerBatch: Math.max(...samples.map((sample) => sample.commits)),
  };
}

it('measures sustained stream batches over a full mirror on the real route', async () => {
  useEventsStore.setState({ hidden: [] });
  useGlobeStore.setState({ terminator: true, opsRoom: false });
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
  const profiled = { ms: 0, commits: 0 };
  applySession('user');
  const router = createMemoryRouter(routes, { initialEntries: ['/'] });
  render(
    <Profiler
      id="app"
      onRender={(_id, _phase, actualDuration) => {
        profiled.ms += actualDuration;
        profiled.commits += 1;
      }}
    >
      <RouterProvider router={router} />
    </Profiler>,
  );
  await screen.findByText('Natural hazards: 1 loaded');
  await waitFor(() => {
    expect(useEventsStore.getState().loaded).toBe(true);
  });
  const base = clock.now - 2 * 86_400_000;
  act(() => {
    useEventsStore
      .getState()
      .applyUpsert(Array.from({ length: FIXTURE_MIRROR_SIZE }, (_, i) => streamEvent(i, base)));
  });
  expect(useEventsStore.getState().list).toHaveLength(FIXTURE_MIRROR_SIZE);
  const client = FakeEventStreamClient.instances[0]!;
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });

  let next = FIXTURE_MIRROR_SIZE;
  const deliver = (messages: readonly SseMessage[]): Sample => {
    for (const message of messages) client.emit(message);
    profiled.ms = 0;
    profiled.commits = 0;
    let mergeMs = 0;
    const started = performance.now();
    act(() => {
      vi.advanceTimersByTime(STREAM_BATCH_MS);
      mergeMs = performance.now() - started;
    });
    const reactMs = performance.now() - started - mergeMs;
    return { mergeMs, reactMs, profilerMs: profiled.ms, commits: profiled.commits };
  };
  const run = (batch: () => SseMessage[]) =>
    summary(Array.from({ length: FIXTURE_BATCHES }, () => deliver(batch())));

  const newIds = run(() => {
    const events = Array.from({ length: FIXTURE_BATCH_SIZE }, () => streamEvent(next++, base));
    return [upsertMessage(events)];
  });
  const existingIds = run(() => {
    const ids = Array.from({ length: FIXTURE_BATCH_SIZE }, (_, i) => next - 1 - i);
    return [upsertMessage(ids.map((id) => streamEvent(id, base, { title: `Updated ${next}` })))];
  });
  const mixed = run(() => {
    const retained = useEventsStore.getState().list;
    const expired = retained.slice(-50).map((event) => event.id);
    const events = Array.from({ length: FIXTURE_BATCH_SIZE - 50 }, () => streamEvent(next++, base));
    return [expireMessage(expired), upsertMessage(events)];
  });

  // Control latency: switch the view mode as each batch lands, every 250 ms, and time the
  // switch to its commit. Outside act(), React schedules work as it would in a browser.
  const environment = globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean };
  environment.IS_REACT_ACT_ENVIRONMENT = false;
  const turn = () =>
    new Promise((resolve) => {
      setImmediate(resolve);
    });
  const toolbar = screen.getByRole('group', { name: 'View mode' });
  const latencies: number[] = [];
  try {
    for (let round = 0; round < FIXTURE_BATCHES; round++) {
      const roundStart = performance.now();
      const events = Array.from({ length: FIXTURE_BATCH_SIZE }, () => streamEvent(next++, base));
      client.emit(upsertMessage(events));
      const target = round % 2 ? 'Globe' : 'Map';
      const button = within(toolbar).getByRole('button', { name: target });
      vi.advanceTimersByTime(STREAM_BATCH_MS);
      const started = performance.now();
      useGlobeStore.getState().setMode(target === 'Globe' ? 'globe' : 'map');
      while (button.getAttribute('aria-pressed') !== 'true') await turn();
      latencies.push(performance.now() - started);
      while (performance.now() - roundStart < STREAM_BATCH_MS) await turn();
    }
  } finally {
    environment.IS_REACT_ACT_ENVIRONMENT = true;
  }
  const controlLatency = {
    medianMs: round(median(latencies)),
    maxMs: round(Math.max(...latencies)),
  };
  await act(async () => {
    await turn();
  });
  expect(useEventsStore.getState().list).toHaveLength(FIXTURE_MIRROR_SIZE);
  expect(useEventsStore.getState().byId[`s${next - 1}`]).toBeDefined();
  process.stdout.write(
    `${JSON.stringify({ kan81: { newIds, existingIds, mixed, controlLatency } })}\n`,
  );
}, 120_000);
