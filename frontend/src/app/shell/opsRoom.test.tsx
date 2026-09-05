import { screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { useGlobeStore } from '@/stores/globe';
import { renderApp } from '@/test/render';

describe('ops room', () => {
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

  it('keeps the chrome on other pages even while the flag is set', async () => {
    useGlobeStore.setState({ opsRoom: true });
    renderApp('/reports', 'user');
    expect(await screen.findByRole('navigation', { name: 'Primary' })).toBeInTheDocument();
    useGlobeStore.setState({ opsRoom: false });
  });
});
