import { act, renderHook } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { beforeEach, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/server';
import { applySession } from '@/test/render';
import { defaultProfile } from '@/test/handlers.profile';
import { researchArea } from '@/test/areaResearchPanel';
import { useAreaResearch } from './useAreaResearch';

beforeEach(() => applySession('user'));

it('requires a current preview and consent even when generation is invoked directly', async () => {
  let calls = 0;
  server.use(
    http.post('/api/report-jobs', () => {
      calls += 1;
      return HttpResponse.json({});
    }),
  );
  const { result } = renderHook(() => useAreaResearch(researchArea, null, defaultProfile), {
    wrapper: MemoryRouter,
  });
  await act(async () => {
    await result.current.generate();
  });
  act(() => result.current.setConsent(true));
  await act(async () => {
    await result.current.generate();
  });
  expect(calls).toBe(0);
});

it.each(['missing', 'invalid', 'long question'] as const)(
  'rejects %s input before any source request',
  async (kind) => {
    let calls = 0;
    server.use(
      http.post('/api/research/runs/plan', () => {
        calls += 1;
        return HttpResponse.json({});
      }),
    );
    const { result } = renderHook(
      () =>
        useAreaResearch(
          kind === 'missing' ? null : researchArea,
          kind === 'invalid' ? 'Invalid boundary.' : null,
          defaultProfile,
        ),
      { wrapper: MemoryRouter },
    );
    if (kind === 'long question') act(() => result.current.setQuestion('x'.repeat(1001)));
    await act(async () => {
      await result.current.checkSources();
    });
    expect(calls).toBe(0);
    expect(result.current.error).toContain(
      kind === 'missing'
        ? 'Complete an area'
        : kind === 'invalid'
          ? 'Invalid boundary'
          : '1,000 characters',
    );
  },
);
