import { beforeEach, describe, expect, it } from 'vitest';

import { liveEvent } from '@/test/fixtures';

import { MAX_CLIENT_EVENTS, filterByWindow, initialEventsState, useEventsStore } from './events';

describe('events store edges', () => {
  beforeEach(() => {
    useEventsStore.setState({ ...initialEventsState });
  });

  it('bounds every merged batch and clears an evicted selection', () => {
    const many = Array.from({ length: MAX_CLIENT_EVENTS + 2 }, (_, index) =>
      liveEvent({
        id: `e${String(index)}`,
        observed_at: new Date(
          Date.UTC(2026, 8, 5, 0, Math.floor(index / 60), index % 60),
        ).toISOString(),
      }),
    );
    useEventsStore.getState().applyUpsert(many);
    expect(useEventsStore.getState().list).toHaveLength(MAX_CLIENT_EVENTS);
    useEventsStore.getState().select('e2');
    useEventsStore
      .getState()
      .applyUpsert([liveEvent({ id: 'late', observed_at: '2027-01-01T00:00:00Z' })]);
    const state = useEventsStore.getState();
    expect(state.list).toHaveLength(MAX_CLIENT_EVENTS);
    expect(state.byId.e0).toBeUndefined();
    expect(state.byId.e1).toBeUndefined();
    expect(state.byId.e2).toBeUndefined();
    expect(state.byId.late).toBeDefined();
    expect(state.selectedId).toBeNull();
  });

  it('retains a refreshed event and its selection when merging at the cap', () => {
    const many = Array.from({ length: MAX_CLIENT_EVENTS }, (_, index) =>
      liveEvent({ id: `e${String(index)}`, observed_at: new Date(index * 1000).toISOString() }),
    );
    useEventsStore.getState().applyUpsert(many);
    useEventsStore.getState().select('e0');
    useEventsStore
      .getState()
      .applyUpsert([
        liveEvent({ id: 'e0', title: 'Updated', observed_at: '2027-01-01T00:00:00Z' }),
        liveEvent({ id: 'new', observed_at: '2027-01-01T00:00:00Z' }),
      ]);
    const state = useEventsStore.getState();
    expect(state.list).toHaveLength(MAX_CLIENT_EVENTS);
    expect(state.byId.e0?.title).toBe('Updated');
    expect(state.byId.e1).toBeUndefined();
    expect(state.selectedId).toBe('e0');
  });

  it('ignores unreadable, unknown and malformed stream messages', () => {
    const { handleStreamMessage } = useEventsStore.getState();
    handleStreamMessage({ event: 'event.upsert', data: 'not json', id: null });
    handleStreamMessage({ event: 'something.else', data: '{}', id: null });
    handleStreamMessage({ event: 'event.upsert', data: '{"events": "nope"}', id: null });
    handleStreamMessage({ event: 'event.expire', data: '{"ids": 5}', id: null });
    expect(useEventsStore.getState().list).toHaveLength(0);
  });

  it('clears the selection when the selected event expires', () => {
    const state = useEventsStore.getState();
    state.applyUpsert([liveEvent({ id: 'x1' }), liveEvent({ id: 'x2' })]);
    state.select('x1');
    state.applyExpire(['x2']);
    expect(useEventsStore.getState().selectedId).toBe('x1');
    state.applyExpire(['x1']);
    expect(useEventsStore.getState().selectedId).toBeNull();
  });

  it('passes everything through when no window is set', () => {
    const events = [liveEvent({ id: 'w1' })];
    expect(filterByWindow(events, null, Date.now())).toBe(events);
  });
});
