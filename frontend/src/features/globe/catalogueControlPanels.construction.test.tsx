import { act, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
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

const reads = vi.hoisted(() => ({ news: 0, traffic: 0 }));
// These body-only getters always return the original value. Counting reads does not
// alter the catalogue, filter state or the output of either real panel builder.
vi.mock('./catalogueControlPanels', async (load) => {
  const actual = await load<typeof import('./catalogueControlPanels')>();
  return {
    ...actual,
    catalogueControlPanels(props: Parameters<typeof actual.catalogueControlPanels>[0]) {
      const news = { ...props.news };
      const value = news.windowHours;
      Object.defineProperty(news, 'windowHours', {
        enumerable: true,
        get: () => {
          reads.news++;
          return value;
        },
      });
      return actual.catalogueControlPanels({ ...props, news });
    },
  };
});
vi.mock('./trafficControlPanels', async (load) => {
  const actual = await load<typeof import('./trafficControlPanels')>();
  return {
    ...actual,
    trafficControlPanels(props: Parameters<typeof actual.trafficControlPanels>[0]) {
      const current = { ...props };
      const value = current.selectionDisabled;
      Object.defineProperty(current, 'selectionDisabled', {
        enumerable: true,
        get: () => {
          reads.traffic++;
          return value;
        },
      });
      return actual.trafficControlPanels(current);
    },
  };
});

beforeEach(() => {
  useEventsStore.setState({ hidden: [] });
  useGlobeStore.setState({ terminator: false, opsRoom: false });
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
  reads.news = 0;
  reads.traffic = 0;
});

it('does not construct closed catalogue content as a batch updates the real route', async () => {
  const { user } = renderApp('/', 'user');
  await screen.findByText('Natural hazards: 1 loaded');
  reads.news = 0;
  act(() => useEventsStore.getState().applyUpsert([liveEvent({ id: 'new-quake' })]));
  expect(screen.getByText('Natural hazards: 2 loaded')).toBeInTheDocument();
  expect(reads.news).toBe(0);
  expect(screen.getByRole('button', { name: 'News briefing' })).toHaveAttribute(
    'aria-expanded',
    'false',
  );
  await user.click(screen.getByRole('button', { name: 'News briefing' }));
  expect(reads.news).toBeGreaterThan(0);
  const regions = screen.getAllByRole('region', { name: 'News briefing' });
  expect(regions).toHaveLength(2);
  for (const region of regions) expect(region).toBeVisible();
});

it('does not construct either closed traffic body, but constructs the selected current body', async () => {
  const { user } = renderApp('/', 'user');
  await screen.findByText('Natural hazards: 1 loaded');
  reads.traffic = 0;
  const vessel = liveEvent({
    id: 'current-ship',
    category: 'maritime',
    subtype: 'vessel_position',
    title: 'Current vessel',
  });
  act(() => useEventsStore.getState().applyUpsert([vessel]));
  expect(reads.traffic).toBe(0);
  await user.click(screen.getByRole('button', { name: 'Boat list' }));
  expect(reads.traffic).toBeGreaterThan(0);
  expect(screen.getByRole('button', { name: /Current vessel/ })).toBeInTheDocument();
  await user.keyboard('{Escape}');
  reads.traffic = 0;
  act(() => useEventsStore.getState().applyExpire([vessel.id]));
  expect(reads.traffic).toBe(0);
  await user.click(screen.getByRole('button', { name: 'Boat list' }));
  expect(screen.queryByRole('button', { name: /Current vessel/ })).not.toBeInTheDocument();
});
