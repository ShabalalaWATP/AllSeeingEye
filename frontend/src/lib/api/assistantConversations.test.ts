import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { eyeAnswer } from '@/components/assistant/assistantFixture';
import { server } from '@/test/server';
import {
  createAssistantConversation,
  getAssistantConversation,
  listAssistantConversations,
} from './assistantConversations';

const id = 'bcbdc71b-4f0a-425a-a708-70d9c79027c9';
const now = '2026-09-13T10:00:00Z';
const turn = {
  question: 'What changed?',
  scope: 'global',
  time_window: 'auto',
  source_categories: null,
  answer: { ...eyeAnswer, continuation_id: null, model: null },
};
const record = {
  id, title: 'My research', turns: [turn], created_at: now, updated_at: now,
  snapshot_notice: 'Private user-controlled chat snapshot.',
};

it('validates a private saved conversation and keeps the save action explicit', async () => {
  let writes = 0;
  server.use(
    http.get('/api/assistant/conversations', () =>
      HttpResponse.json({ items: [{ id, title: record.title, turn_count: 1, created_at: now, updated_at: now }] }),
    ),
    http.get('/api/assistant/conversations/:id', () => HttpResponse.json(record)),
    http.post('/api/assistant/conversations', async ({ request }) => {
      writes++;
      expect(await request.json()).toMatchObject({ title: 'My research', turns: [turn] });
      return HttpResponse.json(record, { status: 201 });
    }),
  );
  expect((await listAssistantConversations()).items).toHaveLength(1);
  expect((await getAssistantConversation(id)).turns[0]?.answer.continuation_id).toBeNull();
  await createAssistantConversation({ title: 'My research', turns: [turn] });
  expect(writes).toBe(1);
});

it('rejects an unexpected saved source category at the API boundary', async () => {
  server.use(
    http.get('/api/assistant/conversations/:id', () =>
      HttpResponse.json({ ...record, turns: [{ ...turn, source_categories: ['secret_source'] }] }),
    ),
  );
  await expect(getAssistantConversation(id)).rejects.toMatchObject({ code: 'invalid_response' });
});
