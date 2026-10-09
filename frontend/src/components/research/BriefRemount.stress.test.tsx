import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';

import type { BriefDraft, ResearchBrief } from '@/lib/api/researchBriefSchema';
import { renderApp } from '@/test/render';
import { reportJob } from '@/test/reportJobFixture';
import { server } from '@/test/server';

const briefId = 'd73c2988-d2ca-4482-9e39-7269e876eaa0';
const editorName = { name: 'Research Brief editor' };

function savedBrief(draft: BriefDraft): ResearchBrief {
  return {
    ...draft,
    identity: {
      id: briefId,
      revision: 1,
      owner_id: 'd2e73f24-a73a-4ee7-b478-f175a05ba96d',
      team_id: draft.team_id,
      title: draft.title,
      created_at: '2026-09-14T10:00:00Z',
      revised_at: '2026-09-14T10:00:00Z',
      preset_id: draft.preset_id,
      preset_version: draft.preset_version,
      schema_version: 1,
      origin: 'authored',
      published: false,
    },
  };
}

// KAN-206: 30 consecutive integration scenarios selected with the full suite.
// Each holds the saved-revision read open until the old editor has unmounted.
it.each(Array.from({ length: 30 }, (_, index) => index + 1))(
  'remounts the saved brief before edit, cancel and exact-revision run (iteration %i)',
  async (iteration) => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    const title = `Port research ${iteration}`;
    let saved: ResearchBrief;
    let runBody: unknown;
    let finishReload!: () => void;
    const reload = new Promise<void>((resolve) => {
      finishReload = resolve;
    });
    server.use(
      http.post('/api/research/briefs', async ({ request }) => {
        saved = savedBrief((await request.json()) as BriefDraft);
        return HttpResponse.json({ brief: saved }, { status: 201 });
      }),
      http.get(`/api/research/briefs/${briefId}/revisions/1`, async () => {
        await reload;
        return HttpResponse.json({ brief: saved });
      }),
      http.post('/api/report-jobs/from-brief', async ({ request }) => {
        runBody = await request.json();
        return HttpResponse.json(reportJob(), { status: 202 });
      }),
    );
    try {
      const { user, router } = renderApp('/research?brief=new', 'user');
      const originalEditor = await screen.findByRole('region', editorName);
      const original = within(originalEditor);
      fireEvent.change(original.getByLabelText('Brief title'), { target: { value: title } });
      fireEvent.change(original.getByLabelText('Main research question'), {
        target: { value: 'What changed at the port?' },
      });
      await user.click(original.getByRole('button', { name: 'Save brief' }));
      await waitFor(() =>
        expect(router.state.location.search).toBe(`?brief=${briefId}&revision=1&stage=run`),
      );
      await waitFor(() => expect(originalEditor).not.toBeInTheDocument());
      expect(await screen.findByText('Loading Research Brief')).toBeVisible();
      expect(screen.queryByRole('region', editorName)).not.toBeInTheDocument();
      expect(confirm).not.toHaveBeenCalled();

      act(() => finishReload());
      const replacement = await screen.findByRole('region', editorName);
      expect(replacement).not.toBe(originalEditor);
      const editor = within(replacement);
      expect(editor.getByText(/Exact saved revision 1/)).toBeVisible();
      await waitFor(() =>
        expect(editor.getByRole('heading', { name: 'Review and run' })).toHaveFocus(),
      );
      const reloadEvent = new Event('beforeunload', { cancelable: true });
      window.dispatchEvent(reloadEvent);
      expect(reloadEvent.defaultPrevented).toBe(false);

      await user.click(editor.getByRole('button', { name: '1 Brief' }));
      expect(editor.getByLabelText('Brief title')).toHaveValue(title);
      fireEvent.change(editor.getByLabelText('Brief title'), { target: { value: 'Unsaved' } });
      await act(() => router.navigate('/research/jobs'));
      expect(confirm).toHaveBeenCalledOnce();
      expect(editor.getByLabelText('Brief title')).toHaveValue('Unsaved');
      await user.click(editor.getByRole('button', { name: '4 Run' }));
      expect(editor.getByRole('button', { name: 'Run once' })).toBeDisabled();
      await user.click(editor.getByRole('button', { name: 'Cancel changes' }));
      expect(editor.getByLabelText('Brief title')).toHaveValue(title);
      await user.click(editor.getByRole('button', { name: 'Run once' }));
      await waitFor(() => expect(runBody).toMatchObject({ brief_id: briefId, revision: 1 }));
      expect(Object.keys(runBody as object).sort()).toEqual(['brief_id', 'request_id', 'revision']);
      expect(confirm).toHaveBeenCalledOnce();
    } finally {
      finishReload();
    }
  },
);
