import { render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { applySession } from '@/test/render';
import { server } from '@/test/server';
import type { AssistantRequest } from '@/lib/api/assistant';
import { assistantAnswerSchema } from '@/lib/api/assistant';
import {
  launchAssistantReportQuestion,
  registerAssistantReportContext,
} from '@/lib/assistantReportContext';
import { EyeAssistant } from './EyeAssistant';
import { eyeAnswer } from './assistantFixture';

const ID = '901e502c-79d0-4274-a39e-458515121302';
const savedAnswer = { ...eyeAnswer, continuation_id: null, model: null };
const reportSelection = {
  id: '7b7b7b7b-7b7b-4b7b-8b7b-7b7b7b7b7b7b',
  version: 3,
  title: 'Harbour report',
  dataCutoff: '2026-09-11T10:00:00Z',
};
const reportAnswer = assistantAnswerSchema.parse({
  ...savedAnswer,
  scope: { mode: 'report', bbox: null, selected: null },
  report: {
    id: reportSelection.id,
    version_id: '8c8c8c8c-8c8c-4c8c-8c8c-8c8c8c8c8c8c',
    version: reportSelection.version,
    title: reportSelection.title,
    data_cutoff: reportSelection.dataCutoff,
  },
});

it('saves explicitly, resumes a labelled snapshot, omits old evidence tokens and confirms deletion', async () => {
  let saved: Record<string, unknown> | null = null;
  let savedBody: Record<string, unknown> | null = null;
  let updates = 0;
  const asks: AssistantRequest[] = [];
  const summary = () => ({
    id: ID,
    title: 'Harbour investigation',
    turn_count: 1,
    created_at: '2026-09-11T10:00:00Z',
    updated_at: '2026-09-11T10:00:00Z',
  });
  server.use(
    http.post('/api/assistant/answer', async ({ request }) => {
      asks.push((await request.json()) as AssistantRequest);
      return HttpResponse.json(eyeAnswer);
    }),
    http.get('/api/assistant/conversations', () =>
      HttpResponse.json({ items: saved ? [summary()] : [] }),
    ),
    http.post('/api/assistant/conversations', async ({ request }) => {
      savedBody = (await request.json()) as Record<string, unknown>;
      const body = savedBody as { turns: { answer: typeof eyeAnswer }[] };
      const { id, title, created_at, updated_at } = summary();
      saved = {
        id,
        title,
        created_at,
        updated_at,
        turns: body.turns.map((turn) => ({ ...turn, answer: savedAnswer })),
        snapshot_notice: 'Saved snapshot. Recheck source links before relying on it.',
      };
      return HttpResponse.json(saved, { status: 201 });
    }),
    http.get(`/api/assistant/conversations/${ID}`, () =>
      saved ? HttpResponse.json(saved) : new HttpResponse(null, { status: 404 }),
    ),
    http.put(`/api/assistant/conversations/${ID}`, async ({ request }) => {
      if (!saved) return new HttpResponse(null, { status: 404 });
      updates++;
      const body = (await request.json()) as { turns: { answer: typeof eyeAnswer }[] };
      saved = {
        ...saved,
        turns: body.turns.map((turn) => ({ ...turn, answer: savedAnswer })),
      };
      return HttpResponse.json(saved);
    }),
    http.delete(`/api/assistant/conversations/${ID}`, () => {
      saved = null;
      return new HttpResponse(null, { status: 204 });
    }),
  );
  applySession('user');
  render(
    <MemoryRouter>
      <EyeAssistant />
    </MemoryRouter>,
  );
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Open Eye assistant' }));
  await user.type(screen.getByLabelText('Ask the Eye'), 'Summarise harbour observations{Enter}');
  await screen.findByText('Two recent vessel observations are available.');
  expect(savedBody).toBeNull();
  await user.click(screen.getByRole('button', { name: 'Saved chats' }));
  await user.type(screen.getByLabelText('Save this chat'), 'Harbour investigation');
  await user.click(screen.getByRole('button', { name: 'Save chat' }));
  expect(await screen.findByText('Conversation saved.')).toBeVisible();
  expect(savedBody).toMatchObject({
    title: 'Harbour investigation',
    turns: [{ question: 'Summarise harbour observations', time_window: 'auto' }],
  });
  await user.click(screen.getByRole('button', { name: 'Resume' }));
  expect(screen.getByText('Replaces current chat')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Cancel' }));
  await user.click(screen.getByRole('button', { name: 'New chat' }));
  await user.click(screen.getByRole('button', { name: 'Saved chats' }));
  await user.click(screen.getByRole('button', { name: 'Resume' }));
  expect(
    await screen.findByText('Saved snapshot. Recheck source links before relying on it.'),
  ).toBeVisible();
  expect(screen.getByText('Saved answer · recheck before use')).toBeVisible();
  expect(screen.getByText('Two recent vessel observations are available.')).toBeVisible();
  await user.type(screen.getByLabelText('Ask the Eye'), 'Which of those can be confirmed?{Enter}');
  await waitFor(() => expect(asks).toHaveLength(2));
  expect(asks[1]).not.toHaveProperty('continuation_id');
  await waitFor(() => expect(screen.getByLabelText('Ask the Eye')).toBeEnabled());
  await user.click(screen.getByRole('button', { name: 'Saved chats' }));
  await user.click(screen.getByRole('button', { name: 'Update saved chat' }));
  expect(await screen.findByText('Conversation saved.')).toBeVisible();
  expect(updates).toBe(1);
  await user.click(screen.getByRole('button', { name: 'Delete' }));
  await user.click(screen.getByRole('button', { name: 'Confirm delete' }));
  expect(await screen.findByText('Saved conversation deleted.')).toBeVisible();
  expect(screen.getByText('No saved conversations yet.')).toBeVisible();
});

it('saves and resumes report Q&A with the exact report edition', async () => {
  let savedBody: Record<string, unknown> | null = null;
  let saved: Record<string, unknown> | null = null;
  const asks: AssistantRequest[] = [];
  server.use(
    http.post('/api/assistant/answer', async ({ request }) => {
      asks.push((await request.json()) as AssistantRequest);
      return HttpResponse.json(reportAnswer);
    }),
    http.get('/api/assistant/conversations', () =>
      HttpResponse.json({
        items: saved
          ? [
              {
                id: ID,
                title: 'Harbour report questions',
                turn_count: 1,
                created_at: '2026-09-11T10:00:00Z',
                updated_at: '2026-09-11T10:00:00Z',
              },
            ]
          : [],
      }),
    ),
    http.post('/api/assistant/conversations', async ({ request }) => {
      savedBody = (await request.json()) as Record<string, unknown>;
      const body = savedBody as { turns: unknown[] };
      saved = {
        id: ID,
        title: 'Harbour report questions',
        created_at: '2026-09-11T10:00:00Z',
        updated_at: '2026-09-11T10:00:00Z',
        turns: body.turns,
        snapshot_notice: 'Saved snapshot. Recheck source links before relying on it.',
      };
      return HttpResponse.json(saved, { status: 201 });
    }),
    http.get(`/api/assistant/conversations/${ID}`, () =>
      saved ? HttpResponse.json(saved) : new HttpResponse(null, { status: 404 }),
    ),
  );
  const unregister = registerAssistantReportContext(reportSelection);
  applySession('user');
  render(
    <MemoryRouter>
      <EyeAssistant />
    </MemoryRouter>,
  );
  launchAssistantReportQuestion(reportSelection);
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: 'Saved chats' }));
  expect(screen.getByText(/saved with the exact report edition and version/)).toBeVisible();
  await user.type(screen.getByLabelText('Ask the Eye'), 'What does this edition conclude?{Enter}');
  await screen.findByText('Two recent vessel observations are available.');
  await user.click(screen.getByRole('button', { name: 'Save chat' }));
  await waitFor(() => expect(savedBody).not.toBeNull());
  expect(savedBody).toMatchObject({
    turns: [
      {
        scope: 'report',
        report: { id: reportSelection.id, version: reportSelection.version },
      },
    ],
  });
  await user.click(screen.getByRole('button', { name: 'New chat' }));
  await user.click(screen.getByRole('button', { name: 'Saved chats' }));
  await user.click(screen.getByRole('button', { name: 'Resume' }));
  expect(await screen.findByText(/FROZEN REPORT · VERSION 3/)).toBeVisible();
  expect(screen.getByText('Two recent vessel observations are available.')).toBeVisible();
  await user.type(screen.getByLabelText('Ask the Eye'), 'What evidence supports that?{Enter}');
  await waitFor(() => expect(asks).toHaveLength(2));
  expect(asks[1]).toMatchObject({
    scope: 'report',
    report: { id: reportSelection.id, version: reportSelection.version },
  });
  unregister();
});
