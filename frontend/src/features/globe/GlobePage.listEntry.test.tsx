import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import { mockWebGl2 } from '@/test/env';
import { MapboxOverlay } from '@/test/fakeDeck';
import { FakeMap } from '@/test/fakeMap';
import { FakeEventStreamClient } from '@/test/fakeStream';
import { liveEvent } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
// Load the lazy route once, outside the per-test timeout.
import './GlobePage';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

const LINK = 'Browse loaded events as a list';

function tabbable(container: HTMLElement): HTMLElement[] {
  return [
    ...container.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), input, select'),
  ].filter((element) => element.tabIndex >= 0);
}

/** The panel's own section, not the inspector region that shares its name. */
function listPanel(): HTMLElement {
  const search = screen.getByRole('searchbox', { name: 'Search loaded records' });
  return search.closest('section')!;
}

describe('globe page heading and direct list entry', () => {
  beforeEach(() => {
    useEventsStore.setState({ hidden: [] });
    useGlobeStore.setState({ mode: 'globe', opsRoom: false });
    server.use(http.get('/api/trackers/conflicts', () => HttpResponse.json({ items: [] })));
    FakeMap.reset();
    MapboxOverlay.reset();
    FakeEventStreamClient.reset();
    mockWebGl2(true);
  });

  it('names the page with one heading that follows the selected view', async () => {
    const { user } = renderApp('/', 'user');
    await screen.findByText('Natural hazards: 1 loaded');
    const heading = screen.getByRole('heading', { level: 1, name: 'Globe view' });
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(heading).toHaveClass('sr-only');
    const toolbar = screen.getByRole('group', { name: 'View mode' });
    await user.click(within(toolbar).getByRole('button', { name: 'Map' }));
    expect(heading).toHaveTextContent('Map view');
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
  });

  it('opens the searchable list in one activation and returns focus to the link', async () => {
    const { user } = renderApp('/', 'user');
    await screen.findByText('Natural hazards: 1 loaded');
    const main = screen.getByRole('main');
    const link = within(main).getByRole('link', { name: LINK });
    // The link is the first stop in main, hidden until it receives keyboard focus.
    expect(tabbable(main)[0]).toBe(link);
    expect(link).toHaveClass('sr-only', 'focus:not-sr-only');
    link.focus();
    await user.keyboard('{Enter}');
    const search = await screen.findByRole('searchbox', { name: 'Search loaded records' });
    await waitFor(() => {
      expect(search).toHaveFocus();
    });
    const panel = listPanel();
    expect(within(panel).getByRole('button', { name: /M4\.2 near Somewhere/ })).toBeVisible();

    await user.keyboard('M4.2');
    expect(within(panel).queryByRole('button', { name: /CVE-2026-0001/ })).toBeNull();
    const record = within(panel).getByRole('button', { name: /M4\.2 near Somewhere/ });
    record.focus();
    await user.keyboard('{Enter}');
    expect(useEventsStore.getState().selectedId).toBe('e1');

    await user.click(screen.getByRole('button', { name: 'Close tool' }));
    expect(screen.queryByRole('searchbox', { name: 'Search loaded records' })).toBeNull();
    expect(link).toHaveFocus();

    // Activating again reopens rather than toggling closed, and Escape also restores focus.
    await user.keyboard('{Enter}');
    await waitFor(() => {
      expect(screen.getByRole('searchbox', { name: 'Search loaded records' })).toHaveFocus();
    });
    await user.keyboard('{Enter}');
    expect(screen.getByRole('searchbox', { name: 'Search loaded records' })).toBeInTheDocument();
    await user.keyboard('{Escape}');
    expect(link).toHaveFocus();
  });

  it('pages through many loaded records by keyboard', async () => {
    server.use(
      http.get('/api/events', () => {
        const items = Array.from({ length: 25 }, (_, i) =>
          liveEvent({ id: `q${i}`, title: `Quake ${i}`, point: { lon: i, lat: i } }),
        );
        return HttpResponse.json({ items, count: items.length });
      }),
    );
    const { user } = renderApp('/', 'user');
    const link = await screen.findByRole('link', { name: LINK });
    await waitFor(() => {
      expect(useEventsStore.getState().list).toHaveLength(25);
    });
    link.focus();
    await user.keyboard('{Enter}');
    const pages = await screen.findByRole('navigation', { name: 'Location quality record pages' });
    within(pages).getByRole('button', { name: 'Next' }).focus();
    await user.keyboard('{Enter}');
    expect(within(pages).getByText('2 / 2')).toBeInTheDocument();
    expect(await screen.findByText('25 matching loaded records, page 2 of 2.')).toBeInTheDocument();
  });

  it('explains an empty loaded set and an empty search, keeping reset and close usable', async () => {
    server.use(http.get('/api/events', () => HttpResponse.json({ items: [], count: 0 })));
    const { user } = renderApp('/', 'user');
    const link = await screen.findByRole('link', { name: LINK });
    await waitFor(() => {
      expect(useEventsStore.getState().loaded).toBe(true);
    });
    link.focus();
    await user.keyboard('{Enter}');
    const panel = await waitFor(listPanel);
    expect(
      within(panel).getByText(/No records are loaded for the current layers, nation and time/),
    ).toBeInTheDocument();
    const search = within(panel).getByRole('searchbox', { name: 'Search loaded records' });
    await user.type(search, 'anything');
    expect(within(panel).getByRole('button', { name: 'Clear search' })).toBeEnabled();
    await user.click(screen.getByRole('button', { name: 'Close tool' }));
    expect(link).toHaveFocus();
  });

  it('offers a search reset when loaded records do not match', async () => {
    const { user } = renderApp('/', 'user');
    const link = await screen.findByRole('link', { name: LINK });
    await screen.findByText('Natural hazards: 1 loaded');
    link.focus();
    await user.keyboard('{Enter}');
    const panel = await waitFor(listPanel);
    await user.keyboard('no such record');
    expect(within(panel).getByText('No records match these filters.')).toBeInTheDocument();
    await user.click(within(panel).getByRole('button', { name: 'Clear search' }));
    const search = within(panel).getByRole('searchbox', { name: 'Search loaded records' });
    expect(search).toHaveValue('');
    expect(search).toHaveFocus();
    expect(within(panel).getByRole('button', { name: /M4\.2 near Somewhere/ })).toBeVisible();
  });

  it('keeps the heading but drops the link in the ops room, where tools are hidden', async () => {
    useGlobeStore.setState({ opsRoom: true });
    renderApp('/', 'user');
    const heading = await screen.findByRole(
      'heading',
      { level: 1, name: 'Globe view' },
      { timeout: 10_000 },
    );
    expect(heading).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: LINK })).toBeNull();
  });
});
