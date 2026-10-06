import { act, renderHook } from '@testing-library/react';
import { expect, it } from 'vitest';

import { liveEventSchema } from '@/lib/api/eventSchemas';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { useEventsStore } from '@/stores/events';
import { liveEvent } from '@/test/fixtures';
import { useDashboardSelection } from './useDashboardSelection';

it.each(['selected', ''])('returns the current selected object for ID %j', (id) => {
  const original = liveEventSchema.parse(liveEvent({ id, category: 'news' }));
  const corrected = Object.freeze({ ...original, title: 'Corrected report', country_iso: 'GB' });
  Object.freeze(original);
  const rows = [original];
  useEventsStore.setState({ selectedId: id, selectionOwner: 'view', list: rows });
  const { result, rerender } = renderHook(({ events }) => useDashboardSelection(events), {
    initialProps: { events: rows },
  });
  expect(result.current.selected).toBe(original);

  rerender({ events: [corrected] });
  expect(result.current.selected).toBe(corrected);
  expect(useEventsStore.getState().selectedId).toBe(id);
  act(() => result.current.select(null));
  expect(result.current.selected).toBeNull();
});

it('keeps a newly selected record while the shown mirror is behind, then resolves or clears it', () => {
  const previous = liveEvent({ id: 'previous' });
  const incoming = liveEvent({ id: 'incoming' });
  const shown = [previous];
  const current = [incoming, previous];
  useEventsStore.setState({ selectedId: 'incoming', selectionOwner: 'view', list: current });
  const { result, rerender } = renderHook(
    ({ events, mirror }) => useDashboardSelection(events, mirror),
    { initialProps: { events: shown, mirror: shown } },
  );
  expect(result.current.selected).toBeNull();
  expect(useEventsStore.getState().selectedId).toBe('incoming');

  rerender({ events: current, mirror: current });
  expect(result.current.selected).toBe(incoming);
  rerender({ events: shown, mirror: current });
  expect(result.current.selected).toBeNull();
  expect(useEventsStore.getState().selectedId).toBeNull();
});

it('clears an expired view-owned selection even before the shown list catches up', () => {
  const event = liveEvent({ id: 'expires' });
  useEventsStore.getState().applyUpsert([event]);
  useEventsStore.getState().select(event.id, 'view');
  const shown = useEventsStore.getState().list;
  const { result } = renderHook(() => useDashboardSelection(shown, shown));
  expect(result.current.selected).toBe(event);

  act(() => useEventsStore.getState().applyExpire([event.id]));
  expect(result.current.selected).toBeNull();
  expect(useEventsStore.getState().selectedId).toBeNull();
});

it.each(['workspace', 'auth', 'unmount'] as const)(
  'clears the view-owned selection on %s invalidation',
  (reason) => {
    const event = liveEvent({ id: 'scoped' });
    const rows = [event];
    useEventsStore.setState({ selectedId: event.id, selectionOwner: 'view', list: rows });
    const { result, unmount } = renderHook(() => useDashboardSelection(rows));
    expect(result.current.selected).toBe(event);

    act(() => {
      if (reason === 'workspace') invalidateWorkspaceAccess();
      else if (reason === 'auth') useAuthStore.setState({ status: 'authenticated' });
      else unmount();
    });
    expect(useEventsStore.getState().selectedId).toBeNull();
  },
);
