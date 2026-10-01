import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { applySession, renderApp } from '@/test/render';
import { jobId, reportJob } from '@/test/reportJobFixture';
import { openAdvancedResearch } from '@/test/researchForm';
import { server } from '@/test/server';

type App = ReturnType<typeof renderApp>;

async function leaveAndReturn(router: App['router'], path: string) {
  await act(() => router.navigate('/research/jobs'));
  await screen.findByRole('heading', { name: 'Research progress' });
  await act(() => router.navigate(path));
}

afterEach(() => vi.restoreAllMocks());

describe('form drafts survive in-app navigation within one session', () => {
  it('restores a research question, depth and advanced mode, and clears them on sign-out', async () => {
    const { user, router } = renderApp('/research', 'user');
    const question = await screen.findByLabelText('Your question');
    await user.type(question, 'Which ports reopened this week?');
    await openAdvancedResearch();
    await leaveAndReturn(router, '/research');
    expect(await screen.findByLabelText('Your question')).toHaveValue(
      'Which ports reopened this week?',
    );
    expect(screen.getByRole('button', { name: 'Advanced options' })).toHaveAttribute(
      'aria-expanded',
      'true',
    );
    act(() => useAuthStore.getState().clearSession());
    applySession('user');
    await act(() => router.navigate('/research/jobs'));
    await act(() => router.navigate('/research'));
    expect(await screen.findByLabelText('Your question')).toHaveValue('');
  });

  it('keeps a research draft for its own link context only', async () => {
    const { user, router } = renderApp('/research', 'user');
    await user.type(await screen.findByLabelText('Your question'), 'Plain draft');
    await act(() => router.navigate('/research?question=Linked%20question'));
    expect(await screen.findByLabelText('Your question')).toHaveValue('Linked question');
    await act(() => router.navigate('/research'));
    expect(await screen.findByLabelText('Your question')).toHaveValue('Plain draft');
  });

  it('restores a new subscription and clears it when workspace access changes', async () => {
    const { user, router } = renderApp('/subscriptions', 'user');
    const name = await screen.findByLabelText('Subscription name');
    await user.type(name, 'Port closures');
    await leaveAndReturn(router, '/subscriptions');
    expect(await screen.findByLabelText('Subscription name')).toHaveValue('Port closures');
    act(() => invalidateWorkspaceAccess());
    await leaveAndReturn(router, '/subscriptions');
    expect(await screen.findByLabelText('Subscription name')).toHaveValue('');
  });

  it('restores a new alert rule and clears it for another account', async () => {
    const { user, router } = renderApp('/warning', 'user');
    const form = await screen.findByRole('form', { name: 'New alert rule' });
    await user.type(within(form).getByLabelText('Alert rule name'), 'Border crossings');
    await user.type(within(form).getByLabelText('Keywords'), 'checkpoint, queue');
    await leaveAndReturn(router, '/warning');
    const restored = await screen.findByRole('form', { name: 'New alert rule' });
    expect(within(restored).getByLabelText('Alert rule name')).toHaveValue('Border crossings');
    expect(within(restored).getByLabelText('Keywords')).toHaveValue('checkpoint, queue');
    act(() => applySession('admin'));
    await leaveAndReturn(router, '/warning');
    await waitFor(() =>
      expect(
        within(screen.getByRole('form', { name: 'New alert rule' })).getByLabelText(
          'Alert rule name',
        ),
      ).toHaveValue(''),
    );
  });

  it('asks before leaving collection plan edits that cannot be restored', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValue(true);
    const { user, router } = renderApp('/research', 'user');
    await user.type(await screen.findByLabelText('Your question'), 'Kept question');
    await openAdvancedResearch();
    await user.click(screen.getByText(/^Collection plan/));
    await user.click(screen.getByRole('checkbox', { name: 'Supply exact search terms' }));
    await act(() => router.navigate('/research/jobs'));
    expect(confirm).toHaveBeenCalledTimes(1);
    expect(confirm.mock.calls[0]![0]).toMatch(/edited collection plan settings will be lost/);
    expect(router.state.location.pathname).toBe('/research');
    await act(() => router.navigate('/research/jobs'));
    await waitFor(() => expect(router.state.location.pathname).toBe('/research/jobs'));
    await act(() => router.navigate('/research'));
    expect(await screen.findByLabelText('Your question')).toHaveValue('Kept question');
    expect(screen.getByRole('checkbox', { name: 'Supply exact search terms' })).not.toBeChecked();
  });

  it('discards the research draft once the server accepts it', async () => {
    server.use(
      http.post('/api/report-jobs', () => HttpResponse.json(reportJob(), { status: 202 })),
    );
    const { user, router } = renderApp('/research', 'user');
    await user.type(await screen.findByLabelText('Your question'), 'Submitted question');
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Start research' })).toBeEnabled(),
    );
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    await waitFor(() => expect(router.state.location.pathname).toBe(`/research/jobs/${jobId}`));
    await screen.findByRole('heading', { name: 'Researching the available evidence' });
    await act(() => router.navigate('/research'));
    expect(await screen.findByLabelText('Your question')).toHaveValue('');
  });
});
