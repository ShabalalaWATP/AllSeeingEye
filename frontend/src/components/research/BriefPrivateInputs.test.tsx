import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import type { BriefDraft, ResearchBrief } from '@/lib/api/researchBriefSchema';
import { newBriefDraft } from '@/lib/researchBriefDraft';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const briefId = 'd73c2988-d2ca-4482-9e39-7269e876eaa0';
const inputId = 'aab87ced-d5d9-4079-9503-d47d5e23b8f9';
const reportId = '33333333-3333-4333-8333-333333333333';

function saved(draft: BriefDraft): ResearchBrief {
  return {
    ...draft,
    identity: {
      id: briefId,
      revision: 1,
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
}

function privateDraft(focus: 'document' | 'media'): BriefDraft {
  const draft = newBriefDraft();
  draft.title = 'Private review';
  draft.question.main = 'What does the evidence show?';
  draft.scope.focus = focus;
  draft.private_inputs = [
    {
      kind: 'session',
      input_id: inputId,
      report_id: null,
      report_version: null,
      expires_at: '2099-01-01T00:00:00Z',
      disclose_to_provider: false,
    },
  ];
  return draft;
}

function serveBrief(draft: BriefDraft) {
  let revised: BriefDraft | null = null;
  server.use(
    http.get(`/api/research/briefs/${briefId}/revisions/1`, () =>
      HttpResponse.json({ brief: saved(draft) }),
    ),
    http.post(`/api/research/briefs/${briefId}/revisions`, async ({ request }) => {
      revised = (await request.json()) as BriefDraft;
      return HttpResponse.json({ brief: saved(revised) }, { status: 201 });
    }),
  );
  return () => revised;
}

it('gates private focus without evidence and links to working document and media upload controls', async () => {
  const { user, router } = renderApp('/research?brief=new', 'user');
  const editor = within(await screen.findByRole('region', { name: 'Research Brief editor' }));
  await user.click(editor.getByRole('button', { name: '2 Scope' }));
  expect(editor.getByRole('option', { name: 'Private document' })).toBeDisabled();
  expect(editor.getByRole('option', { name: 'Private media' })).toBeDisabled();
  expect(editor.getByLabelText('Research focus')).toHaveAccessibleDescription(
    /Private document and media focus require existing private evidence/,
  );
  await user.selectOptions(editor.getByLabelText('Research focus'), 'document');
  expect(editor.getByLabelText('Research focus')).toHaveValue('general');
  const link = editor.getByRole('link', { name: 'Open Research uploads' });
  expect(link).toHaveAttribute('href', '/research');
  expect(
    editor.getByText(/expand Advanced options and choose Private document or Private media/),
  ).toBeVisible();
  await user.click(link);
  expect(router.state.location.pathname).toBe('/research');
  expect(router.state.location.search).toBe('');
  const form = within(await screen.findByRole('form', { name: 'Research a question' }));
  await user.click(form.getByRole('button', { name: 'Advanced options' }));
  for (const focus of ['document', 'media']) {
    await user.selectOptions(form.getByLabelText('Research focus'), focus);
    expect(form.getByLabelText('Document or media')).toBeVisible();
    expect(form.getByLabelText('Document or media')).toBeEnabled();
  }
});

it.each(['document', 'media'] as const)(
  'preserves a saved private %s definition and its references when editing and saving',
  async (focus) => {
    const draft = privateDraft(focus);
    if (focus === 'media') {
      draft.private_inputs = [
        {
          kind: 'durable_report',
          input_id: null,
          report_id: reportId,
          report_version: 2,
          expires_at: null,
          disclose_to_provider: true,
        },
      ];
    }
    const revised = serveBrief(draft);
    const { user } = renderApp(`/research?brief=${briefId}&revision=1`, 'user');
    const editor = within(await screen.findByRole('region', { name: 'Research Brief editor' }));
    await user.click(editor.getByRole('button', { name: '2 Scope' }));
    expect(editor.getByLabelText('Research focus')).toHaveValue(focus);
    expect(editor.getByRole('option', { name: 'Private document' })).toBeEnabled();
    expect(editor.getByRole('option', { name: 'Private media' })).toBeEnabled();
    fireEvent.change(editor.getByLabelText('Lookback hours'), { target: { value: '48' } });
    await user.click(editor.getByRole('button', { name: 'Save brief' }));
    await waitFor(() => expect(revised()).not.toBeNull());
    expect(revised()?.scope).toEqual(draft.scope);
    expect(revised()?.private_inputs).toEqual(draft.private_inputs);
    expect(revised()?.observation.lookback_hours).toBe(48);
    expect(screen.queryByText(inputId)).not.toBeInTheDocument();
    expect(screen.queryByText(reportId)).not.toBeInTheDocument();
  },
);

it('keeps private focus available for an existing parent-report definition without session inputs', async () => {
  const draft = privateDraft('document');
  draft.private_inputs = [];
  draft.scope.parent_report_id = reportId;
  draft.scope.parent_version = 2;
  const revised = serveBrief(draft);
  const { user } = renderApp(`/research?brief=${briefId}&revision=1`, 'user');
  const editor = within(await screen.findByRole('region', { name: 'Research Brief editor' }));
  await user.click(editor.getByRole('button', { name: '2 Scope' }));
  expect(editor.getByRole('option', { name: 'Private document' })).toBeEnabled();
  expect(editor.getByLabelText('Research focus')).toHaveValue('document');
  fireEvent.change(editor.getByLabelText('Lookback hours'), { target: { value: '48' } });
  await user.click(editor.getByRole('button', { name: 'Save brief' }));
  await waitFor(() => expect(revised()).not.toBeNull());
  expect(revised()?.scope).toEqual(draft.scope);
  expect(revised()?.private_inputs).toEqual([]);
});

it('explains the separate upload recovery for expired input without erasing the saved reference', async () => {
  const draft = privateDraft('document');
  draft.private_inputs[0]!.expires_at = '2020-01-01T00:00:00Z';
  const revised = serveBrief(draft);
  const { user } = renderApp(`/research?brief=${briefId}&revision=1`, 'user');
  const editor = within(await screen.findByRole('region', { name: 'Research Brief editor' }));
  await user.click(editor.getByRole('button', { name: '4 Run' }));
  expect(editor.getByRole('button', { name: 'Run once' })).toBeDisabled();
  expect(editor.getByRole('button', { name: 'Run once' })).toHaveAccessibleDescription(
    /A private input has expired.*This editor cannot renew attachments.*separate research/,
  );
  expect(editor.getByRole('link', { name: 'Open Research' })).toHaveAttribute('href', '/research');
  await user.click(editor.getByRole('button', { name: '1 Brief' }));
  fireEvent.change(editor.getByLabelText('Brief title'), { target: { value: 'Updated review' } });
  await user.click(editor.getByRole('button', { name: 'Save brief' }));
  await waitFor(() => expect(revised()).not.toBeNull());
  expect(revised()?.private_inputs).toEqual(draft.private_inputs);
  expect(revised()?.scope).toEqual(draft.scope);
  expect(screen.queryByText(inputId)).not.toBeInTheDocument();
});
