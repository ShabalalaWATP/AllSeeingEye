import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it, vi } from 'vitest';
import { applySession, renderApp } from '@/test/render';
import { countries, liveEvent } from '@/test/fixtures';
import { server } from '@/test/server';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import { prepareCyberMap } from '@/stores/cyberFilters';
import type { CyberCountryContext } from './cyberCountryContext';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));
import './GlobePage';

const claim = liveEvent({
  id: 'cyber-claim',
  title: 'Example bank: unverified claim',
  category: 'cyber',
  subtype: 'ransomware',
  source_id: 'ransomware_live',
  country_iso: 'GB',
  geo_confidence: 'country',
  point: null,
  published_at: new Date().toISOString(),
});
const outage = {
  ...claim,
  id: 'cyber-outage',
  title: 'Reported connectivity signal',
  subtype: 'outage',
  source_id: 'ioda_outages',
};
interface Layer {
  id: string;
  props: { data: unknown[]; onClick: (info: { object: unknown }) => boolean };
}
const layer = (id: string) =>
  (MapboxOverlay.instances[0]?.props.layers as Layer[] | undefined)?.find((item) => item.id === id);

beforeEach(() => {
  FakeMap.reset();
  MapboxOverlay.reset();
  FakeEventStreamClient.reset();
  mockWebGl2(true);
  server.use(http.get('/api/trackers/conflicts', () => HttpResponse.json({ items: [] })));
});

it.each(['globe', 'map'] as const)(
  'shows selectable country context after one Cyber toggle on the %s',
  async (mode) => {
    useGlobeStore.setState({ mode });
    server.use(
      http.get('/api/events', () => HttpResponse.json({ items: [claim, outage], count: 2 })),
    );
    const { user } = renderApp('/', 'user');
    const toggle = await screen.findByRole('switch', { name: 'Cyber 0' });
    expect(toggle).toHaveAttribute('aria-checked', 'false');
    expect(layer('cyber-country-context-icons')).toBeUndefined();
    await user.click(toggle);
    await screen.findByRole('switch', { name: 'Cyber 2' });
    await waitFor(() => expect(layer('cyber-country-context-icons')?.props.data).toHaveLength(1));
    await user.click(screen.getByRole('button', { name: 'Cyber filters' }));
    const panel = screen.getByRole('region', { name: 'Cyber threat intelligence filters' });
    expect(within(panel).getByText(/not incident coordinates/)).toBeVisible();
    expect(
      within(panel).getByRole('checkbox', { name: 'Show approximate country context' }),
    ).toBeChecked();
    const group = layer('cyber-country-context-icons')!.props.data[0] as CyberCountryContext;
    act(() => {
      layer('cyber-country-context-icons')!.props.onClick({ object: group });
    });
    const inspector = screen.getByRole('complementary', { name: 'Cyber country context details' });
    expect(
      within(inspector).getByText(/country reference, not an incident coordinate/),
    ).toBeVisible();
    expect(group.events).toHaveLength(2);
    await user.click(within(inspector).getByRole('button', { name: /Example bank/ }));
    const eventDetails = screen.getByRole('complementary', { name: 'Event details' });
    expect(within(eventDetails).getByText('Country only, no incident position')).toBeVisible();
    expect(layer('context-selected-position')).toBeUndefined();
    await user.selectOptions(
      within(panel).getByRole('combobox', { name: 'Record type' }),
      'outage_signal',
    );
    expect(screen.queryByRole('complementary', { name: 'Event details' })).not.toBeInTheDocument();
    await waitFor(() =>
      expect(
        (layer('cyber-country-context-icons')!.props.data[0] as CyberCountryContext).events,
      ).toHaveLength(1),
    );
    await user.click(screen.getByRole('switch', { name: 'Cyber 1' }));
    expect(layer('cyber-country-context-icons')).toBeUndefined();
    await user.click(screen.getByRole('switch', { name: 'Cyber 0' }));
    await waitFor(() => expect(layer('cyber-country-context-icons')?.props.data).toHaveLength(1));
    await user.click(
      within(panel).getByRole('checkbox', { name: 'Show approximate country context' }),
    );
    expect(layer('cyber-country-context-icons')).toBeUndefined();
    await user.click(screen.getByRole('switch', { name: 'Cyber 1' }));
    await user.click(screen.getByRole('switch', { name: 'Cyber 0' }));
    await screen.findByRole('switch', { name: 'Cyber 1' });
    expect(layer('cyber-country-context-icons')).toBeUndefined();
  },
);

it('focuses page-selected country context without injecting a fabricated live-event coordinate', async () => {
  applySession('user');
  prepareCyberMap({ country: 'GB', event: claim, kind: 'ransomware_claim' });
  server.use(http.get('/api/events', () => HttpResponse.json({ items: [], count: 0 })));
  renderApp('/');
  const details = await screen.findByRole('complementary', { name: 'Event details' });
  expect(within(details).getByText(claim.title)).toBeVisible();
  expect(useEventsStore.getState().byId[claim.id]).toBeUndefined();
  expect(layer('context-selected-position')).toBeUndefined();
  expect(FakeMap.instances[0]!.flyTo).toHaveBeenCalledWith(
    expect.objectContaining({
      center: countries.find((country) => country.iso2 === 'GB')!.centroid,
    }),
  );
});
