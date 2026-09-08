import { expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { useEventsStore } from './events';
import { EventUpdateBatch } from './events.stream';

it('coalesces a realistic burst over a full client mirror without changing retained records', () => {
  const initial = Array.from({ length: 5_000 }, (_, i) => liveEvent({ id: `initial-${i}` }));
  const messages = Array.from({ length: 200 }, (_, group) => ({
    event: 'event.upsert',
    id: null,
    data: JSON.stringify({
      events: Array.from({ length: 10 }, (_, index) =>
        liveEvent({ id: `initial-${group * 10 + index}`, title: 'Updated' }),
      ),
    }),
  }));
  useEventsStore.getState().reset();
  useEventsStore.getState().applyUpsert(initial);
  const direct = vi.fn();
  const offDirect = useEventsStore.subscribe(direct);
  for (const message of messages) useEventsStore.getState().handleStreamMessage(message);
  offDirect();
  const expected = useEventsStore.getState().list;
  useEventsStore.getState().reset();
  useEventsStore.getState().applyUpsert(initial);
  const batched = vi.fn();
  const offBatch = useEventsStore.subscribe(batched);
  const batch = new EventUpdateBatch(useEventsStore.getState);
  for (const message of messages) {
    batch.receive(message);
    batch.receive({ event: 'source.health', data: '{}', id: null });
  }
  batch.flush();
  offBatch();
  expect(useEventsStore.getState().list).toEqual(expected);
  expect(direct).toHaveBeenCalledTimes(200);
  expect(batched).toHaveBeenCalledOnce();
  useEventsStore.getState().reset();
});
