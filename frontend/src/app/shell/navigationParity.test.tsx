/**
 * One destination definition feeds the desktop rail, the mobile navigation dialog and
 * the command palette, so the three never disagree on a label or an address.
 */
import { cleanup, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { navigationEntries, savedViews } from '@/lib/workspaceNavigation';
import { renderApp, type Session } from '@/test/render';

import { commandTargets } from './commandTargets';

let narrow = false;

beforeEach(() => {
  const base = window.matchMedia.bind(window);
  vi.spyOn(window, 'matchMedia').mockImplementation((query) => {
    const media = base(query);
    if (query.includes('max-width')) Object.defineProperty(media, 'matches', { get: () => narrow });
    return media;
  });
  // jsdom has no native dialog top layer. Real browser checks cover its focus trap.
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.open = true;
      this.querySelector<HTMLElement>('button')?.focus();
    },
  });
  Object.defineProperty(HTMLDialogElement.prototype, 'close', {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.open = false;
    },
  });
});

afterEach(() => {
  // Unmount while the dialog stubs still exist, so an open dialog can close.
  cleanup();
  narrow = false;
  vi.restoreAllMocks();
  Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal');
  Reflect.deleteProperty(HTMLDialogElement.prototype, 'close');
});

type Entry = readonly [label: string, href: string];

function linksIn(nav: HTMLElement): Entry[] {
  return within(nav)
    .getAllByRole('link')
    .map((link) => [link.textContent, link.getAttribute('href') ?? ''] as const);
}

function expected(admin: boolean): Entry[] {
  return navigationEntries({ admin }).map((entry) => [entry.label, entry.to] as const);
}

function paletteEntries(admin: boolean): Entry[] {
  return commandTargets({ admin })
    .filter((target) => target.id.startsWith('page:'))
    .map((target) => [target.label, target.to] as const);
}

async function desktopEntries(session: Session): Promise<Entry[]> {
  renderApp('/', session);
  return linksIn(await screen.findByRole('navigation', { name: 'Primary' }));
}

async function mobileEntries(session: Session): Promise<Entry[]> {
  narrow = true;
  const { user } = renderApp('/', session);
  await user.click(await screen.findByRole('button', { name: 'Open navigation' }));
  const dialog = screen.getByRole('dialog', { name: 'Navigation' });
  return linksIn(within(dialog).getByRole('navigation', { name: 'Primary' }));
}

describe('one navigation definition', () => {
  it.each([
    ['user', false],
    ['admin', true],
  ] as const)(
    'gives the %s the same labels and addresses on the rail, mobile and palette',
    async (session, admin) => {
      const definition = expected(admin);
      expect(await desktopEntries(session)).toEqual(definition);
      expect(paletteEntries(admin)).toEqual(definition);
    },
  );

  it.each([
    ['user', false],
    ['admin', true],
  ] as const)('gives the %s the same entries in the mobile dialog', async (session, admin) => {
    expect(await mobileEntries(session)).toEqual(expected(admin));
  });

  it('nests each supported watch type under Watches instead of beside it', async () => {
    renderApp('/', 'user');
    const nav = await screen.findByRole('navigation', { name: 'Primary' });
    const watches = within(nav).getByRole('link', { name: 'Watches' });
    const item = watches.closest('li');
    expect(item).not.toBeNull();
    const children = within(item!).getByRole('list', { name: 'In Watches' });
    expect(linksIn(children)).toEqual([
      ['Subscriptions', '/subscriptions'],
      ['Alerts', '/warning'],
      ['Plans and areas', '/direction'],
      ['Annotation monitors', '/annotation-monitors'],
    ]);
    // Research progress belongs to Research, not beside it.
    const research = within(nav).getByRole('link', { name: 'Research' }).closest('li');
    expect(linksIn(within(research!).getByRole('list', { name: 'In Research' }))).toEqual([
      ['Research progress', '/research/jobs'],
    ]);
    // No two entries share a label or an address.
    const all = linksIn(nav);
    expect(new Set(all.map(([label]) => label)).size).toBe(all.length);
    expect(new Set(all.map(([, href]) => href)).size).toBe(all.length);
    // Alerts is never called Warning in navigation.
    expect(within(nav).queryByText(/warning/i)).not.toBeInTheDocument();
  });

  it('keeps every previously available destination reachable', () => {
    const reachable = new Set(commandTargets().map((target) => target.to));
    for (const route of [
      '/',
      '/research',
      '/research/saved',
      '/research/jobs',
      '/geolocation',
      '/geolocation/saved',
      '/watches',
      '/subscriptions',
      '/subscriptions/saved',
      '/warning',
      '/direction',
      '/annotation-monitors',
      '/trackers',
      '/trackers/social',
      '/trackers/aviation',
      '/trackers/maritime',
      '/trackers/space',
      '/trackers/figures',
      '/conflicts/ukraine',
      '/cyber',
      '/economy',
      '/teams',
    ]) {
      expect(reachable, route).toContain(route);
    }
    // Saved work is one search away, under the group that owns it.
    expect(savedViews().map((view) => [view.label, view.group])).toEqual([
      ['Saved research', 'Research'],
      ['Saved assessments', 'Research'],
      ['Saved updates', 'Watches'],
    ]);
  });

  it('never offers or mounts administration for an ordinary account', async () => {
    narrow = true;
    const { user } = renderApp('/watches', 'user');
    await user.click(await screen.findByRole('button', { name: 'Open navigation' }));
    const dialog = screen.getByRole('dialog', { name: 'Navigation' });
    expect(within(dialog).queryByRole('link', { name: 'Administration' })).not.toBeInTheDocument();
    expect(commandTargets().some((target) => target.to.startsWith('/admin'))).toBe(false);
    expect(navigationEntries({ admin: false }).some((entry) => entry.to === '/admin')).toBe(false);
    expect(screen.queryByRole('navigation', { name: 'Administration' })).not.toBeInTheDocument();
  });

  it('lets the keyboard open, traverse and close mobile navigation, restoring focus', async () => {
    narrow = true;
    const { user, router } = renderApp('/watches', 'user');
    const trigger = await screen.findByRole('button', { name: 'Open navigation' });
    trigger.focus();
    await user.keyboard('{Enter}');
    const dialog = screen.getByRole('dialog', { name: 'Navigation' });
    expect(within(dialog).getByRole('button', { name: 'Close navigation' })).toHaveFocus();
    // Close, then the home link, the animation pause, Find anything and the first destination,
    // in reading order.
    await user.tab();
    expect(within(dialog).getByRole('link', { name: 'The All Seeing Eye' })).toHaveFocus();
    await user.tab();
    expect(within(dialog).getByRole('button', { name: 'Pause animation' })).toHaveFocus();
    await user.tab();
    expect(within(dialog).getByRole('button', { name: /Find anything/ })).toHaveFocus();
    await user.tab();
    expect(within(dialog).getByRole('link', { name: 'Map' })).toHaveFocus();
    await user.click(within(dialog).getByRole('button', { name: 'Close navigation' }));
    await waitFor(() => {
      expect(trigger).toHaveFocus();
    });
    await user.keyboard('{Enter}');
    const reopened = screen.getByRole('dialog', { name: 'Navigation' });
    within(reopened).getByRole('link', { name: 'Alerts' }).focus();
    await user.keyboard('{Enter}');
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/warning');
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
