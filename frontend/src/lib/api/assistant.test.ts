import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import { apiError } from '@/test/handlers';
import { eyeAnswer } from '@/components/assistant/assistantFixture';
import { askAssistant } from './assistant';
import { bindSession, resetSessionBinding } from './client';

afterEach(resetSessionBinding);

it('refreshes an expired session without automatically repeating a paid assistant request', async () => {
  let token = 'stale';
  const authorisations: (string | null)[] = [];
  const refresh = vi.fn(() => {
    token = 'fresh';
    return Promise.resolve(token);
  });
  const lost = vi.fn();
  bindSession({ getAccessToken: () => token, refreshAccessToken: refresh, onSessionLost: lost });
  server.use(
    http.post('/api/assistant/answer', ({ request }) => {
      authorisations.push(request.headers.get('Authorization'));
      if (authorisations.length === 1) return apiError(401, 'unauthenticated', 'Session expired.');
      return HttpResponse.json(eyeAnswer);
    }),
  );
  const question = { question: 'What do the retained sources show?', scope: 'global' as const };
  await expect(askAssistant(question, new AbortController().signal)).rejects.toMatchObject({
    code: 'request_retry_required',
  });
  expect(authorisations).toEqual(['Bearer stale']);
  expect(refresh).toHaveBeenCalledTimes(1);
  expect(lost).not.toHaveBeenCalled();

  await expect(askAssistant(question, new AbortController().signal)).resolves.toEqual(eyeAnswer);
  expect(authorisations).toEqual(['Bearer stale', 'Bearer fresh']);
});
