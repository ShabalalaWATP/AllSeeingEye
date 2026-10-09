import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

let narrow = true;
let signOuts = 0;

beforeEach(() => {
  narrow = true;
  signOuts = 0;
  const base = window.matchMedia.bind(window);
  vi.spyOn(window, 'matchMedia').mockImplementation((query) => {
    const media = base(query);
    if (query.includes('max-width')) Object.defineProperty(media, 'matches', { get: () => narrow });
    return media;
  });
  server.use(
    http.post('/api/auth/logout', () => {
      signOuts += 1;
      return new HttpResponse(null, { status: 204 });
    }),
  );
});

afterEach(() => {
  vi.restoreAllMocks();
});

function menuOf(trigger: HTMLElement): HTMLElement {
  const menu = document.getElementById(trigger.getAttribute('aria-controls') ?? '');
  if (menu === null) throw new Error('The menu is not controlled by its trigger.');
  return menu;
}

async function openShell(path = '/research') {
  const view = renderApp(path, 'user');
  const header = (await screen.findByRole('button', { name: 'Open navigation' })).closest('header');
  if (header === null) throw new Error('The top bar is missing.');
  return { ...view, header };
}

describe('narrow account menu', () => {
  it('keeps navigation and the bell in the bar and moves account actions into a menu', async () => {
    const { header } = await openShell();
    const bar = within(header);
    expect(await bar.findByRole('button', { name: /^Notifications/ })).toBeInTheDocument();
    expect(bar.queryByRole('button', { name: 'Logout' })).not.toBeInTheDocument();
    expect(bar.queryByRole('link', { name: 'Your settings' })).not.toBeInTheDocument();
    const trigger = bar.getByRole('button', { name: 'Account menu' });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(trigger).toHaveClass('min-h-11', 'min-w-11');
  });

  it('opens with focus on the first item, moves with arrows and closes on Escape', async () => {
    const { user } = await openShell();
    const trigger = screen.getByRole('button', { name: 'Account menu' });
    await user.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    const menu = menuOf(trigger);
    const profile = within(menu).getByRole('link', { name: 'Your profile' });
    const logout = within(menu).getByRole('button', { name: 'Logout' });
    expect(profile).toHaveFocus();
    expect(profile).toHaveClass('min-h-11');
    expect(logout).toHaveClass('min-h-11');
    await user.keyboard('{ArrowDown}');
    expect(within(menu).getByRole('link', { name: 'Your settings' })).toHaveFocus();
    await user.keyboard('{End}');
    expect(logout).toHaveFocus();
    await user.keyboard('{ArrowDown}');
    expect(profile).toHaveFocus();
    await user.keyboard('{Escape}');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(menu).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    expect(signOuts).toBe(0);
  });

  it('closes on an outside click and returns focus to the trigger', async () => {
    const { user } = await openShell();
    const trigger = screen.getByRole('button', { name: 'Account menu' });
    await user.click(trigger);
    await user.click(screen.getByRole('main'));
    expect(screen.queryByRole('link', { name: 'Your settings' })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(screen.getByRole('link', { name: 'Your profile' })).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(signOuts).toBe(0);
  });

  it('follows Settings like any link and closes the menu', async () => {
    const { user, router } = await openShell();
    await user.click(screen.getByRole('button', { name: 'Account menu' }));
    await user.click(screen.getByRole('link', { name: 'Your settings' }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/settings');
    });
    expect(screen.queryByRole('link', { name: 'Your settings' })).not.toBeInTheDocument();
    expect(signOuts).toBe(0);
    expect(useAuthStore.getState().status).toBe('authenticated');
  });

  it('clears protected content immediately and waits for the requested server sign-out', async () => {
    let finish: () => void = () => undefined;
    server.use(
      http.post('/api/auth/logout', async () => {
        signOuts += 1;
        await new Promise<void>((resolve) => {
          finish = resolve;
        });
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user, router } = await openShell();
    const trigger = screen.getByRole('button', { name: 'Account menu' });
    await user.click(trigger);
    expect(signOuts).toBe(0);
    const menu = within(menuOf(trigger));
    await user.click(menu.getByRole('button', { name: 'Logout' }));
    await waitFor(() => expect(signOuts).toBe(1));
    expect(useAuthStore.getState().status).toBe('anonymous');
    expect(useAuthStore.getState().pendingLogout).not.toBeNull();
    expect(trigger).not.toBeInTheDocument();
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    await act(async () => {
      finish();
      await useAuthStore.getState().pendingLogout;
    });
    expect(useAuthStore.getState().pendingLogout).toBeNull();
    expect(signOuts).toBe(1);
  });

  it('still ends the local session when the server cannot record the sign-out', async () => {
    server.use(http.post('/api/auth/logout', () => new HttpResponse(null, { status: 500 })));
    const { user, router } = await openShell();
    await user.click(screen.getByRole('button', { name: 'Account menu' }));
    await user.click(screen.getByRole('button', { name: 'Logout' }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/login');
    });
    expect(useAuthStore.getState().status).toBe('anonymous');
  });

  it('leaves the desktop bar unchanged', async () => {
    narrow = false;
    renderApp('/research', 'user');
    await screen.findByRole('navigation', { name: 'Primary' });
    expect(screen.queryByRole('button', { name: 'Account menu' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Your settings' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Logout' })).toBeInTheDocument();
  });
});
