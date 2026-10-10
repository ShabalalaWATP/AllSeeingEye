import { act, renderHook, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { useGlobeStore } from '@/stores/globe';
import { renderApp } from '@/test/render';

import { useOpsRoomRoute } from './useOpsRoomRoute';

describe('ops room', () => {
  it('can exit with a pointer or touch without a hardware keyboard', async () => {
    const { user } = renderApp('/', 'user');
    expect(await screen.findByRole('navigation', { name: 'Primary' })).toBeInTheDocument();
    await user.keyboard('o');
    await user.click(await screen.findByRole('button', { name: /^Ops room · Esc to exit/ }));
    expect(useGlobeStore.getState().opsRoom).toBe(false);
    expect(await screen.findByRole('navigation', { name: 'Primary' })).toBeInTheDocument();
  });
  it('drops the chrome, shows the live alerts and leaves on Escape', async () => {
    const { user } = renderApp('/', 'user');
    expect(await screen.findByRole('navigation', { name: 'Primary' })).toBeInTheDocument();
    await user.keyboard('o');
    await waitFor(() => {
      expect(screen.queryByRole('navigation', { name: 'Primary' })).not.toBeInTheDocument();
    });
    expect(useGlobeStore.getState().opsRoom).toBe(true);
    const strip = await screen.findByRole('complementary', { name: 'Unacknowledged alerts' });
    expect(within(strip).getByText('Kharkiv strikes: 3 items in the last 6 h')).toBeInTheDocument();
    expect(screen.getByText('Ops room · Esc to exit')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Logout' })).not.toBeInTheDocument();
    await user.keyboard('{Escape}');
    expect(await screen.findByRole('navigation', { name: 'Primary' })).toBeInTheDocument();
    expect(useGlobeStore.getState().opsRoom).toBe(false);
  });

  it('ends when another route opens, so returning to the map does not resume it', async () => {
    const { user, router } = renderApp('/', 'user');
    expect(await screen.findByRole('navigation', { name: 'Primary' })).toBeInTheDocument();
    await user.keyboard('o');
    await waitFor(() => {
      expect(screen.queryByRole('navigation', { name: 'Primary' })).not.toBeInTheDocument();
    });
    // Leaving by any route, such as the search palette, ends it.
    await act(() => router.navigate('/reports'));
    expect(await screen.findByRole('navigation', { name: 'Primary' })).toBeInTheDocument();
    await waitFor(() => expect(useGlobeStore.getState().opsRoom).toBe(false));
  });

  it('survives arriving at the map, so the shortcut still works from other pages', () => {
    const { rerender } = renderHook(({ path }) => useOpsRoomRoute(path), {
      initialProps: { path: '/reports' },
    });
    // The shortcut sets the flag while the old page is still showing, then arrives home.
    act(() => useGlobeStore.getState().setOpsRoom(true));
    rerender({ path: '/' });
    expect(useGlobeStore.getState().opsRoom).toBe(true);
    rerender({ path: '/research' });
    expect(useGlobeStore.getState().opsRoom).toBe(false);
  });

  it('keeps the chrome on other pages even while the flag is set', async () => {
    useGlobeStore.setState({ opsRoom: true });
    renderApp('/reports', 'user');
    expect(await screen.findByRole('navigation', { name: 'Primary' })).toBeInTheDocument();
    useGlobeStore.setState({ opsRoom: false });
  });
});
