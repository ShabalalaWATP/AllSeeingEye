import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { useGlobeStore } from '@/stores/globe';
import { alert } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { adminUser, tokenFor } from '@/test/fixtures';
import * as warningApi from '@/lib/api/warning';

afterEach(() => useGlobeStore.setState({ opsRoom: false }));

describe('ops-room alert strip', () => {
  it('hides revoked alerts immediately and discards a late response from an older revision', async () => {
    let release: () => void = () => undefined;
    const pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    const oldPage = { items: [alert], unacknowledged: 1 };
    const delayedPage = pending.then(() => oldPage);
    const fetch = vi
      .spyOn(warningApi, 'fetchAlerts')
      .mockResolvedValueOnce(oldPage)
      .mockReturnValueOnce(delayedPage)
      .mockResolvedValue({ items: [], unacknowledged: 0 });
    useGlobeStore.setState({ opsRoom: true });
    renderApp('/', 'user');
    expect(
      await screen.findByRole('complementary', { name: 'Unacknowledged alerts' }),
    ).toBeVisible();
    act(() => {
      invalidateWorkspaceAccess();
    });
    expect(
      screen.queryByRole('complementary', { name: 'Unacknowledged alerts' }),
    ).not.toBeInTheDocument();
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(2);
    });
    act(() => {
      invalidateWorkspaceAccess();
    });
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3));
    await act(async () => {
      release();
      await delayedPage;
    });
    expect(
      screen.queryByRole('complementary', { name: 'Unacknowledged alerts' }),
    ).not.toBeInTheDocument();
  });

  it('removes wall-screen alert content immediately when the account changes', async () => {
    useGlobeStore.setState({ opsRoom: true });
    renderApp('/', 'user');
    await screen.findByRole('complementary', { name: 'Unacknowledged alerts' });
    server.use(
      http.get('/api/warning/alerts', () => HttpResponse.json({ items: [], unacknowledged: 0 })),
    );
    act(() => {
      useAuthStore.getState().setSession(tokenFor(adminUser));
    });
    expect(
      screen.queryByRole('complementary', { name: 'Unacknowledged alerts' }),
    ).not.toBeInTheDocument();
    useGlobeStore.setState({ opsRoom: false });
  });
  it('does not fetch alerts in the regular workspace', async () => {
    const fetch = vi.spyOn(warningApi, 'fetchAlerts');
    renderApp('/reports', 'user');
    await screen.findByRole('heading', { name: 'Saved reports' });
    // The rail links to alerts, but nothing in the regular workspace shows a live count.
    expect(screen.queryByRole('link', { name: /unacknowledged/ })).not.toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('shows three alerts on the wall and counts the rest', async () => {
    const many = [1, 2, 3, 4].map((n) => ({
      ...alert,
      id: `${String(n)}1111111-1111-4111-8111-111111111111`,
      title: `Alert ${String(n)}`,
      summary: n === 4 ? '' : alert.summary,
    }));
    server.use(
      http.get('/api/warning/alerts', () =>
        HttpResponse.json({ items: many, unacknowledged: many.length }),
      ),
    );
    useGlobeStore.setState({ opsRoom: true });
    renderApp('/', 'user');
    const strip = await screen.findByRole('complementary', { name: 'Unacknowledged alerts' });
    expect(within(strip).getByText('Alert 1')).toBeInTheDocument();
    expect(within(strip).queryByText('Alert 4')).not.toBeInTheDocument();
    expect(within(strip).getByText('1 more on the warning page')).toBeInTheDocument();
    useGlobeStore.setState({ opsRoom: false });
  });
});
