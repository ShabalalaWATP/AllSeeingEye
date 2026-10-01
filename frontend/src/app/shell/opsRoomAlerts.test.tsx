import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { useGlobeStore } from '@/stores/globe';
import { bellAlerts, bellSummary } from '@/test/fixtures.bell';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { adminUser, tokenFor } from '@/test/fixtures';
import * as bellApi from '@/lib/api/bell';

afterEach(() => useGlobeStore.setState({ opsRoom: false }));

describe('ops-room alert strip', () => {
  it('hides revoked alerts immediately and discards a late response from an older revision', async () => {
    let release: () => void = () => undefined;
    const pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    const oldPage = bellSummary();
    const delayedPage = pending.then(() => oldPage);
    const fetch = vi
      .spyOn(bellApi, 'fetchBell')
      .mockResolvedValueOnce(oldPage)
      .mockReturnValueOnce(delayedPage)
      .mockResolvedValue(bellSummary([]));
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
    server.use(http.get('/api/bell', () => HttpResponse.json(bellSummary([]))));
    act(() => {
      useAuthStore.getState().setSession(tokenFor(adminUser));
    });
    expect(
      screen.queryByRole('complementary', { name: 'Unacknowledged alerts' }),
    ).not.toBeInTheDocument();
    useGlobeStore.setState({ opsRoom: false });
  });
  it('gives the regular workspace a bell count rather than the wall-screen strip', async () => {
    const fetch = vi.spyOn(bellApi, 'fetchBell');
    renderApp('/research/saved', 'user');
    await screen.findByRole('heading', { name: 'Saved research' });
    expect(
      await screen.findByRole('button', { name: 'Notifications, 1 unread' }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('complementary', { name: 'Unacknowledged alerts' }),
    ).not.toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('shows three alerts on the wall and counts the rest', async () => {
    const many = bellAlerts(4).map((item, index) =>
      index === 3 ? { ...item, summary: '' } : item,
    );
    server.use(http.get('/api/bell', () => HttpResponse.json(bellSummary(many))));
    useGlobeStore.setState({ opsRoom: true });
    renderApp('/', 'user');
    const strip = await screen.findByRole('complementary', { name: 'Unacknowledged alerts' });
    expect(within(strip).getByText('Alert 1')).toBeInTheDocument();
    expect(within(strip).queryByText('Alert 4')).not.toBeInTheDocument();
    expect(within(strip).getByText('1 more on the warning page')).toBeInTheDocument();
    useGlobeStore.setState({ opsRoom: false });
  });
});
