import { screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { commandTargets, matchTargets } from '@/app/shell/commandTargets';
import { startHereKey } from '@/lib/startHere';
import { adminUser, plainUser } from '@/test/fixtures';
import { renderApp, type Session } from '@/test/render';
import { server } from '@/test/server';

let narrow = false;

beforeEach(() => {
  const base = window.matchMedia.bind(window);
  vi.spyOn(window, 'matchMedia').mockImplementation((query) => {
    const media = base(query);
    if (query.includes('max-width')) Object.defineProperty(media, 'matches', { get: () => narrow });
    return media;
  });
});

afterEach(() => {
  narrow = false;
  vi.restoreAllMocks();
});

async function startHere() {
  return screen.findByRole('complementary', { name: 'Start here' });
}

async function openMap(session: Session) {
  const view = renderApp('/', session);
  await screen.findByRole('navigation', { name: 'Primary' });
  return view;
}

describe('Start here', () => {
  it('shows once per account until that account dismisses it', async () => {
    localStorage.setItem('unrelated', 'kept');
    const reads = vi.spyOn(Storage.prototype, 'getItem');
    const first = await openMap('user');
    const card = await startHere();
    for (const step of ['Inspect a map item', 'Ask a research question', 'Set up a subscription'])
      expect(within(card).getByRole('heading', { name: step })).toBeInTheDocument();
    expect(within(card).getByRole('link', { name: 'Go to Research' })).toHaveAttribute(
      'href',
      '/research',
    );
    expect(within(card).getByRole('link', { name: 'Go to Subscriptions' })).toHaveAttribute(
      'href',
      '/subscriptions',
    );
    expect(within(card).getByRole('link', { name: 'Read the user guide' })).toHaveAttribute(
      'href',
      '/help',
    );
    await first.user.click(within(card).getByRole('button', { name: 'Dismiss Start here' }));
    expect(screen.queryByRole('complementary', { name: 'Start here' })).not.toBeInTheDocument();
    expect(localStorage.getItem(startHereKey(plainUser.id))).toBe('dismissed');
    expect(localStorage.getItem('unrelated')).toBe('kept');
    first.unmount();

    // The same account stays dismissed on the next visit.
    const second = await openMap('user');
    expect(screen.queryByRole('complementary', { name: 'Start here' })).not.toBeInTheDocument();
    second.unmount();

    // Another account on the same browser still sees it, and never reads the first key.
    reads.mockClear();
    await openMap('admin');
    expect(await startHere()).toBeInTheDocument();
    const keys = reads.mock.calls.map(([key]) => key).filter((key) => key.includes('start-here'));
    expect(keys.length).toBeGreaterThan(0);
    expect(keys.every((key) => key === startHereKey(adminUser.id))).toBe(true);
  });

  it('reopens from Help and the account menu reaches Help', async () => {
    localStorage.setItem(startHereKey(plainUser.id), 'dismissed');
    narrow = true;
    const { user, router } = renderApp('/research', 'user');
    await user.click(await screen.findByRole('button', { name: 'Account menu' }));
    await user.click(screen.getByRole('link', { name: 'Help and guide' }));
    await screen.findByRole('heading', { name: 'Help and guide', level: 1 });
    expect(router.state.location.pathname).toBe('/help');
    await user.click(screen.getByRole('button', { name: 'Show Start here again' }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/');
    });
    expect(await startHere()).toBeInTheDocument();
    expect(localStorage.getItem(startHereKey(plainUser.id))).toBe('shown');
  });

  it('offers Help on wide screens beside the profile and settings links', async () => {
    renderApp('/research', 'user');
    expect(await screen.findByRole('link', { name: 'Help and guide' })).toHaveAttribute(
      'href',
      '/help',
    );
  });

  it('is found in the palette as Help and as the user guide', () => {
    const targets = commandTargets();
    expect(matchTargets(targets, 'help')[0]).toMatchObject({
      label: 'Help and guide',
      to: '/help',
    });
    expect(matchTargets(targets, 'user guide')[0]).toMatchObject({ to: '/help' });
  });

  it('never starts collection or a model call', async () => {
    const methods: string[] = [];
    const record = ({ request }: { request: Request }) => {
      methods.push(`${request.method} ${new URL(request.url).pathname}`);
    };
    server.events.on('request:start', record);
    const { user } = await openMap('user');
    const card = await startHere();
    await user.click(within(card).getByRole('link', { name: 'Read the user guide' }));
    await screen.findByRole('heading', { name: 'Help and guide', level: 1 });
    server.events.removeListener('request:start', record);
    expect(methods.filter((entry) => !entry.startsWith('GET '))).toEqual([]);
    expect(methods.some((entry) => /reports|research|assistant|schedules/.test(entry))).toBe(false);
  });

  it('summarises the core loop and every workspace by its navigation name', async () => {
    renderApp('/help', 'user');
    await screen.findByRole('heading', { name: 'Help and guide', level: 1 });
    const loop = screen.getByRole('list', { name: 'The core loop' });
    expect(within(loop).getAllByRole('listitem')).toHaveLength(5);
    const places = screen.getByRole('region', { name: 'Where things are' });
    for (const label of ['Research', 'Watches', 'Alerts', 'Live monitor', 'Teams'])
      expect(within(places).getByText(label, { selector: 'dt' })).toBeInTheDocument();
    expect(document.title).toBe('Help and guide · The All Seeing Eye');
  });
});
