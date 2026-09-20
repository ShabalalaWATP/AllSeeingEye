import { act, renderHook, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';

import type { BriefSummary } from '@/lib/api/researchBriefSchema';
import * as briefs from '@/lib/api/researchBriefs';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { applySession, renderApp } from '@/test/render';
import { server } from '@/test/server';
import { useBriefLibrary } from './useBriefLibrary';

const items: BriefSummary[] = Array.from({ length: 51 }, (_, index) => ({
  id: `d73c2988-d2ca-4482-9e39-${String(index).padStart(12, '0')}`,
  revision: 1,
  owner_id: 'd2e73f24-a73a-4ee7-b478-f175a05ba96d',
  team_id: null,
  title: `Saved brief ${index + 1}`,
  schema_version: 1,
  origin: 'authored',
  published: false,
  created_at: '2026-09-14T10:00:00Z',
  revised_at: '2026-09-14T10:00:00Z',
}));

it.each(['library', 'editor'] as const)(
  'pages saved briefs from the %s entry point',
  async (entry) => {
    const offsets: number[] = [];
    server.use(
      http.get('/api/research/briefs', ({ request }) => {
        const offset = Number(new URL(request.url).searchParams.get('offset') ?? 0);
        offsets.push(offset);
        return HttpResponse.json({ items: items.slice(offset, offset + 50), limit: 50, offset });
      }),
    );
    const { user } = renderApp(
      `/research?brief=${entry === 'library' ? 'library' : 'new'}`,
      'user',
    );
    if (entry === 'editor')
      await user.click(await screen.findByRole('link', { name: 'Choose a saved brief' }));
    expect(await screen.findByRole('link', { name: 'Saved brief 1 (revision 1)' })).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Next briefs' }));
    const last = await screen.findByRole('link', { name: 'Saved brief 51 (revision 1)' });
    expect(last).toHaveAttribute('href', `/research?brief=${items[50]?.id ?? ''}&revision=1`);
    expect(
      screen.queryByRole('link', { name: 'Saved brief 1 (revision 1)' }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Next briefs' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Previous briefs' }));
    await waitFor(() =>
      expect(screen.getByRole('link', { name: 'Saved brief 1 (revision 1)' })).toBeVisible(),
    );
    expect(offsets).toEqual([0, 50, 0]);
  },
);

it('retries a failed later page without returning to the first page', async () => {
  const offsets: number[] = [];
  let fail = true;
  server.use(
    http.get('/api/research/briefs', ({ request }) => {
      const offset = Number(new URL(request.url).searchParams.get('offset') ?? 0);
      offsets.push(offset);
      if (offset === 50 && fail) {
        fail = false;
        return HttpResponse.error();
      }
      return HttpResponse.json({ items: items.slice(offset, offset + 50), offset, limit: 50 });
    }),
  );
  const { user } = renderApp('/research?brief=library', 'user');
  await screen.findByRole('link', { name: 'Saved brief 1 (revision 1)' });
  await user.click(screen.getByRole('button', { name: 'Next briefs' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('The server could not be reached.');
  expect(screen.getByText('Page 2')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Retry briefs' }));
  expect(await screen.findByRole('link', { name: 'Saved brief 51 (revision 1)' })).toBeVisible();
  expect(offsets).toEqual([0, 50, 50]);
});

it.each(['workspace', 'account'] as const)(
  'restarts pagination and ignores stale pages after %s changes',
  async (change) => {
    applySession('user');
    type Page = Awaited<ReturnType<typeof briefs.fetchBriefs>>;
    let finish!: (page: Page) => void;
    const fetch = vi
      .spyOn(briefs, 'fetchBriefs')
      .mockResolvedValueOnce({ items: items.slice(0, 50), offset: 0, limit: 50 })
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            finish = resolve;
          }),
      )
      .mockResolvedValueOnce({
        items: [{ ...items[0]!, title: 'Current authority brief' }],
        offset: 0,
        limit: 50,
      });
    const { result } = renderHook(useBriefLibrary);
    await waitFor(() => expect(result.current.canNext).toBe(true));
    act(() => result.current.next());
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    act(() => {
      if (change === 'workspace') invalidateWorkspaceAccess();
      else applySession('admin');
    });
    expect(fetch.mock.calls[1]?.[0].aborted).toBe(true);
    await waitFor(() =>
      expect(result.current.data?.items[0]?.title).toBe('Current authority brief'),
    );
    expect(result.current.pageNumber).toBe(1);
    expect(fetch.mock.calls[2]?.[1]).toBe(0);
    await act(async () => {
      finish({ items: items.slice(50), offset: 50, limit: 50 });
      await Promise.resolve();
    });
    expect(result.current.data?.items[0]?.title).toBe('Current authority brief');
  },
);
