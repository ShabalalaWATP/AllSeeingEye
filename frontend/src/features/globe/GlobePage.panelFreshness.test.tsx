import { act, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { liveEvent } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import './GlobePage';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

beforeEach(() => {
  useEventsStore.setState({ hidden: [] });
  useGlobeStore.setState({ mode: 'globe', terminator: false, opsRoom: false });
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
});

it('opens current News scope after correction and expiry while its body is closed', async () => {
  const { user } = renderApp('/', 'user');
  await screen.findByText('Natural hazards: 1 loaded');
  const located = liveEvent({
    id: 'located-report',
    category: 'news',
    source_id: 'bbc_world',
    country_iso: 'GB',
    published_at: new Date().toISOString(),
    geo_confidence: 'city',
    title: 'Earlier report',
  });
  const reference = { ...located, id: 'country-report', geo_confidence: 'country' as const };
  act(() => useEventsStore.getState().applyUpsert([located, reference]));
  await user.click(screen.getByRole('button', { name: 'News briefing' }));
  expect(screen.getByText(/1 located reports · 1 country references/)).toBeVisible();
  await user.keyboard('{Escape}');
  const corrected = {
    ...located,
    title: 'Current report',
    point: null,
    geo_confidence: 'none' as const,
  };
  act(() => useEventsStore.getState().applyBatch([reference.id], [corrected]));
  await user.click(screen.getByRole('button', { name: 'News briefing' }));
  expect(screen.getByText(/0 located reports · 0 country references/)).toBeVisible();
  expect(useEventsStore.getState().byId[located.id]).toBe(corrected);
  expect(useEventsStore.getState().byId[reference.id]).toBeUndefined();
});

it('keeps selected corrections, expiry and access invalidation active while bodies stay closed', async () => {
  renderApp('/', 'user');
  await screen.findByText('Natural hazards: 1 loaded');
  const original = liveEvent({ id: 'selected-report', title: 'Original observation' });
  act(() => {
    useEventsStore.getState().applyUpsert([original]);
    useEventsStore.getState().select(original.id, 'view');
  });
  expect(screen.getByRole('heading', { name: original.title })).toBeVisible();
  const current = { ...original, title: 'Current observation', point: { lon: 30, lat: 50 } };
  act(() => useEventsStore.getState().applyUpsert([current]));
  expect(screen.getByRole('heading', { name: current.title })).toBeVisible();
  expect(screen.queryByRole('heading', { name: original.title })).not.toBeInTheDocument();
  act(() => useEventsStore.getState().applyExpire([current.id]));
  expect(screen.queryByRole('complementary', { name: 'Event details' })).not.toBeInTheDocument();
  expect(useEventsStore.getState().selectedId).toBeNull();
  act(() => {
    useEventsStore.getState().applyUpsert([current]);
    useEventsStore.getState().select(current.id, 'view');
  });
  expect(screen.getByRole('heading', { name: current.title })).toBeVisible();
  act(() => invalidateWorkspaceAccess());
  expect(screen.queryByRole('complementary', { name: 'Event details' })).not.toBeInTheDocument();
  expect(useEventsStore.getState().selectedId).toBeNull();
  expect(screen.queryByRole('region', { name: 'News briefing' })).not.toBeInTheDocument();
});
