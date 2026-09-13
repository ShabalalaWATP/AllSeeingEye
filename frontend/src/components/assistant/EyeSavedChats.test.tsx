import { render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { applySession } from '@/test/render';
import { server } from '@/test/server';
import type { AssistantRequest } from '@/lib/api/assistant';
import { EyeAssistant } from './EyeAssistant';
import { eyeAnswer } from './assistantFixture';

const ID = '901e502c-79d0-4274-a39e-458515121302';
const savedAnswer = { ...eyeAnswer, continuation_id: null, model: null };

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
