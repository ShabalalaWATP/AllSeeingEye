import { act, renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { plainUser, reportSummary, tokenFor } from '@/test/fixtures';
import { server } from '@/test/server';

import { useReportSearch } from './useReportSearch';

it('clears search text and results on revocation, including an in-flight response', async () => {
  useAuthStore.getState().setSession(tokenFor(plainUser));
  let release!: () => void;
  const delayed = new Promise<void>((resolve) => {
    release = resolve;
  });
  let calls = 0;
  server.use(
    http.get('/api/report-search', () =>
      HttpResponse.json({ available: true, indexed: 1, total: 1, limit: 1000, batch_size: 8 }),
    ),
    http.post('/api/report-search/query', async () => {
      calls += 1;
      if (calls === 2) await delayed;
      return HttpResponse.json({
        items: [{ report: reportSummary, score: 0.8 }],
        indexed: 1,
        total: 1,
      });
    }),
  );
  const { result } = renderHook(() => useReportSearch());
  await waitFor(() => expect(result.current.status.data?.available).toBe(true));
  act(() => result.current.setQuery('Confidential question'));
  await act(async () => {
    await result.current.search.run();
  });
  expect(result.current.results?.items).toHaveLength(1);
  act(() => {
    void result.current.search.run();
  });
  await waitFor(() => expect(calls).toBe(2));
  act(() => invalidateWorkspaceAccess());
  expect(result.current.results).toBeNull();
  expect(result.current.query).toBe('');
  expect(result.current.submittedQuery).toBe('');
  await act(async () => {
    release();
    await delayed;
  });
  await waitFor(() => expect(result.current.search.busy).toBe(false));
  expect(result.current.results).toBeNull();
});
