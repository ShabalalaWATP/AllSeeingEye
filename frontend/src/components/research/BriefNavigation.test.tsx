import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';

import * as briefs from '@/lib/api/researchBriefs';
import type { ResearchBrief } from '@/lib/api/researchBriefSchema';
import { newBriefDraft } from '@/lib/researchBriefDraft';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { applySession, renderApp } from '@/test/render';
import { server } from '@/test/server';

const path = '/research?brief=new';
const title = 'Private port research draft';
const question = 'Which terminals reopened this week?';

async function editNewBrief() {
  const view = renderApp(path, 'user');
  fireEvent.change(await screen.findByLabelText('Brief title'), { target: { value: title } });
  fireEvent.change(screen.getByLabelText('Main research question'), {
    target: { value: question },
  });
  return view;
}

function reloadWouldLoseDraft() {
  const event = new Event('beforeunload', { cancelable: true });
  window.dispatchEvent(event);
  return event.defaultPrevented;
}

it('asks before My briefs, preserves cancelled edits and discards only after confirmed leave', async () => {
  const confirm = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValue(true);
  server.use(
    http.get('/api/research/presets', () =>
      HttpResponse.json({ schema_version: 1, items: [], lens_choices: [], lens_rule: '' }),
    ),
    http.get('/api/research/briefs', () => HttpResponse.json({ items: [], limit: 50, offset: 0 })),
  );
  const { user, router } = await editNewBrief();
  await user.click(screen.getByRole('button', { name: 'Browse presets' }));
  await user.click(screen.getByRole('link', { name: 'My briefs' }));
  expect(confirm).toHaveBeenCalledOnce();
  expect(confirm.mock.calls[0]?.[0]).toMatch(/unsaved.*brief/i);
  expect(router.state.location.search).toBe('?brief=new');
  expect(screen.getByLabelText('Brief title')).toHaveValue(title);
  expect(screen.getByLabelText('Main research question')).toHaveValue(question);
  await user.click(screen.getByRole('link', { name: 'My briefs' }));
  expect(await screen.findByRole('heading', { name: 'My Research Briefs' })).toBeVisible();
  await act(() => router.navigate(-1));
  expect(await screen.findByLabelText('Brief title')).toHaveValue('');
  expect(screen.getByLabelText('Main research question')).toHaveValue('');
});

it('protects a draft on other route changes and reload, then allows deliberate discard', async () => {
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
  const { user, router } = await editNewBrief();
  expect(reloadWouldLoseDraft()).toBe(true);
  await act(() => router.navigate('/research/jobs'));
  expect(confirm).toHaveBeenCalledOnce();
  expect(router.state.location.search).toBe('?brief=new');
  await user.click(screen.getByRole('button', { name: 'Cancel changes' }));
  expect(screen.getByLabelText('Brief title')).toHaveValue('');
  expect(reloadWouldLoseDraft()).toBe(false);
  await act(() => router.navigate('/research/jobs'));
  await screen.findByRole('heading', { name: 'Research progress' });
  expect(confirm).toHaveBeenCalledOnce();
});

it('does not warn for an untouched brief or an ordinary stage change', async () => {
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
  const { user, router } = renderApp(path, 'user');
  await screen.findByLabelText('Brief title');
  expect(reloadWouldLoseDraft()).toBe(false);
  await user.click(screen.getByRole('button', { name: 'Continue to Scope' }));
  await act(() => router.navigate('/research/jobs'));
  await screen.findByRole('heading', { name: 'Research progress' });
  expect(confirm).not.toHaveBeenCalled();
});

it('releases successful-save navigation and protects subsequent edits again', async () => {
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
  const saved: ResearchBrief = {
    ...newBriefDraft(),
    question: { main: question, requirements: [], exclusions: [] },
    identity: {
      id: 'd73c2988-d2ca-4482-9e39-7269e876eaa0',
      revision: 1,
      owner_id: 'd2e73f24-a73a-4ee7-b478-f175a05ba96d',
      team_id: null,
      title,
      created_at: '2026-09-14T10:00:00Z',
      revised_at: '2026-09-14T10:00:00Z',
      preset_id: null,
      preset_version: null,
      schema_version: 1,
      origin: 'authored',
      published: false,
    },
  };
  vi.spyOn(briefs, 'createBrief').mockResolvedValue(saved);
  vi.spyOn(briefs, 'fetchBrief').mockResolvedValue(saved);
  const { user, router } = await editNewBrief();
  const originalEditor = screen.getByRole('region', { name: 'Research Brief editor' });
  await user.click(screen.getByRole('button', { name: 'Save brief' }));
  await waitFor(() => expect(router.state.location.search).toContain(`brief=${saved.identity.id}`));
  // Saved text also appears in the outgoing editor before the route reload commits.
  await waitFor(() => expect(originalEditor).not.toBeInTheDocument());
  await screen.findByText('Exact saved revision 1.', { exact: false });
  expect(confirm).not.toHaveBeenCalled();
  expect(reloadWouldLoseDraft()).toBe(false);
  await user.click(screen.getByRole('button', { name: '1 Brief' }));
  fireEvent.change(screen.getByLabelText('Brief title'), { target: { value: 'Next revision' } });
  await act(() => router.navigate('/research/jobs'));
  expect(confirm).toHaveBeenCalledOnce();
  expect(screen.getByLabelText('Brief title')).toHaveValue('Next revision');
});

it.each(['logout', 'account', 'access'] as const)(
  'clears private edits on %s without blocking authority changes or storing the draft',
  async (change) => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    const { router } = await editNewBrief();
    expect(router.state.location.search).toBe('?brief=new');
    expect(JSON.stringify(localStorage)).not.toContain(title);
    expect(JSON.stringify(sessionStorage)).not.toContain(title);
    await act(async () => {
      if (change === 'logout') useAuthStore.getState().clearSession();
      else if (change === 'account') applySession('admin');
      else invalidateWorkspaceAccess();
      await Promise.resolve();
    });
    expect(screen.queryByDisplayValue(title)).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue(question)).not.toBeInTheDocument();
    expect(confirm).not.toHaveBeenCalled();
    act(() => applySession('user'));
    await act(() => router.navigate(path));
    expect(await screen.findByLabelText('Brief title')).toHaveValue('');
    expect(screen.getByLabelText('Main research question')).toHaveValue('');
    expect(reloadWouldLoseDraft()).toBe(false);
  },
);
