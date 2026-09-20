import { act, render, renderHook, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';

import type { ResearchBrief } from '@/lib/api/researchBriefSchema';
import { newBriefDraft } from '@/lib/researchBriefDraft';
import * as briefs from '@/lib/api/researchBriefs';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { applySession } from '@/test/render';
import { reportJob } from '@/test/reportJobFixture';
import { server } from '@/test/server';
import { BriefEditor } from './BriefEditor';
import { useBriefRun } from './useBriefRun';

const draft = newBriefDraft();
draft.title = 'Port watch';
draft.question.main = 'What changed at the port?';
const saved: ResearchBrief = {
  ...draft,
  identity: {
    id: 'd73c2988-d2ca-4482-9e39-7269e876eaa0',
    revision: 2,
    owner_id: 'd2e73f24-a73a-4ee7-b478-f175a05ba96d',
    team_id: null,
    title: draft.title,
    created_at: '2026-09-14T10:00:00Z',
    revised_at: '2026-09-14T10:00:00Z',
    preset_id: null,
    preset_version: null,
    schema_version: 1,
    origin: 'authored',
    published: false,
  },
};

it('recovers the admitted job after a lost response, then starts a distinct deliberate run', async () => {
  const requests: string[] = [];
  const admitted = new Map<string, ReturnType<typeof reportJob>>();
  server.use(
    http.post('/api/report-jobs/from-brief', async ({ request }) => {
      const body = (await request.json()) as {
        request_id: string;
        brief_id: string;
        revision: number;
      };
      expect(body).toMatchObject({ brief_id: saved.identity.id, revision: 2 });
      requests.push(body.request_id);
      if (!admitted.has(body.request_id)) admitted.set(body.request_id, reportJob());
      if (requests.length === 1) return HttpResponse.error();
      return HttpResponse.json(admitted.get(body.request_id), { status: 202 });
    }),
  );
  applySession('user');
  const user = userEvent.setup();
  render(
    <MemoryRouter>
      <BriefEditor
        initial={{ draft, brief: saved, copy: false, mapTitle: null }}
        initialStep="run"
        onSaved={vi.fn()}
      />
    </MemoryRouter>,
  );
  await user.click(screen.getByRole('button', { name: 'Run once' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('The server could not be reached.');
  await user.click(screen.getByRole('button', { name: /^(Run once|Retry research run)$/ }));
  expect(await screen.findByRole('link', { name: 'Open research job' })).toBeVisible();
  expect(requests[1]).toBe(requests[0]);
  expect(admitted.size).toBe(1);
  await user.click(screen.getByRole('button', { name: 'Run once' }));
  await waitFor(() => expect(requests).toHaveLength(3));
  expect(requests[2]).not.toBe(requests[1]);
  expect(admitted.size).toBe(2);
});

it.each(['revision', 'workspace', 'account'] as const)(
  'does not reuse an unresolved attempt after a %s change',
  async (change) => {
    applySession('user');
    const run = vi.spyOn(briefs, 'runBrief').mockRejectedValueOnce(new Error('Lost response'));
    const { result, rerender } = renderHook(({ brief }) => useBriefRun(brief), {
      initialProps: { brief: saved },
    });
    await act(async () => {
      await result.current.run();
    });
    expect(result.current.error).not.toBeNull();
    act(() => {
      if (change === 'revision')
        rerender({ brief: { ...saved, identity: { ...saved.identity, revision: 3 } } });
      else if (change === 'workspace') invalidateWorkspaceAccess();
      else applySession('admin');
    });
    expect(result.current.error).toBeNull();
    run.mockResolvedValueOnce(reportJob());
    await act(async () => {
      await result.current.run();
    });
    expect(run.mock.calls[1]?.[2]).not.toBe(run.mock.calls[0]?.[2]);
    expect(run.mock.calls[1]?.[0].identity.revision).toBe(change === 'revision' ? 3 : 2);
  },
);

it('aborts a pending admission and ignores its late response after access changes', async () => {
  applySession('user');
  let finish!: (job: ReturnType<typeof reportJob>) => void;
  const run = vi.spyOn(briefs, 'runBrief').mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const { result } = renderHook(() => useBriefRun(saved));
  let pending!: ReturnType<typeof result.current.run>;
  act(() => {
    pending = result.current.run();
  });
  expect(result.current.busy).toBe(true);
  act(() => invalidateWorkspaceAccess());
  expect(run.mock.calls[0]?.[1].aborted).toBe(true);
  expect(result.current.busy).toBe(false);
  await act(async () => {
    finish(reportJob());
    await pending;
  });
  expect(result.current.jobId).toBeNull();
  expect(result.current.error).toBeNull();
});
