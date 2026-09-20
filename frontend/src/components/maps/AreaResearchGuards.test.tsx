import { act, renderHook, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { beforeEach, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/server';
import { applySession } from '@/test/render';
import { defaultProfile } from '@/test/handlers.profile';
import { areaPreview, researchArea } from '@/test/areaResearchPanel';
import { prepareAreaResearchHandoff, readAreaResearchHandoff } from '@/lib/areaResearchDraft';
import type { ResearchPlanInput } from '@/lib/api/researchPlan';
import { useAreaResearch } from './useAreaResearch';

beforeEach(() => applySession('user'));

it('rejects an empty explicit source selection before contacting the planner', async () => {
  const { result } = renderHook(() => useAreaResearch(researchArea, null, defaultProfile), {
    wrapper: MemoryRouter,
  });
  act(() => result.current.setSourceIds([]));
  await act(() => result.current.checkSources());
  expect(result.current.error).toContain('Select at least one research source');
});

it('does not hand off or request a source check until preferences are available', async () => {
  const { result } = renderHook(() => useAreaResearch(researchArea, null, null), {
    wrapper: MemoryRouter,
  });
  await act(() => result.current.checkSources());
  expect(result.current.prepareHandoff()).toBe(false);
  expect(result.current.busy).toBe(false);
  expect(readAreaResearchHandoff()).toBeNull();
});

it('rejects a source preview that silently selects an excluded provider', async () => {
  server.use(
    http.post('/api/research/runs/plan', async ({ request }) =>
      HttpResponse.json(areaPreview((await request.json()) as ResearchPlanInput)),
    ),
  );
  const { result } = renderHook(() => useAreaResearch(researchArea, null, defaultProfile), {
    wrapper: MemoryRouter,
  });
  act(() => result.current.setSourceIds(['research-firms']));
  await act(() => result.current.checkSources());
  expect(result.current.error).toContain('does not match this area');
  expect(result.current.preview).toBeNull();
});

it('preserves an unpreviewed fixed interval in both the source request and handoff', async () => {
  const interval = { since: '2026-09-01T00:00:00Z', until: '2026-09-02T00:00:00Z' };
  prepareAreaResearchHandoff(researchArea, interval, defaultProfile);
  let input: ResearchPlanInput | null = null;
  server.use(
    http.post('/api/research/runs/plan', async ({ request }) => {
      input = (await request.json()) as ResearchPlanInput;
      return HttpResponse.json(areaPreview(input));
    }),
  );
  const { result } = renderHook(() => useAreaResearch(researchArea, null, defaultProfile), {
    wrapper: MemoryRouter,
  });
  act(() => expect(result.current.prepareHandoff()).toBe(true));
  expect(result.current.fixedInterval).toEqual(interval);
  await act(() => result.current.checkSources());
  expect(input).toMatchObject(interval);
  act(() => result.current.setDays(3));
  expect(result.current.fixedInterval).toBeNull();
  act(() => expect(result.current.prepareHandoff()).toBe(true));
});

it('reports handoff validation failure without replacing the previous draft', () => {
  prepareAreaResearchHandoff(researchArea);
  const existing = readAreaResearchHandoff();
  const oversized = structuredClone(researchArea);
  oversized.features[0]!.properties = { label: 'x'.repeat(17000) };
  const { result } = renderHook(() => useAreaResearch(oversized, null, defaultProfile), {
    wrapper: MemoryRouter,
  });
  act(() => expect(result.current.prepareHandoff()).toBe(false));
  expect(result.current.error).toContain('16 KiB');
  expect(readAreaResearchHandoff()).toBe(existing);
});

it('deduplicates same-tick checks and prevents handoff while source support is pending', async () => {
  let finish: () => void = () => undefined;
  const pending = new Promise<void>((resolve) => {
    finish = resolve;
  });
  let requests = 0;
  server.use(
    http.post('/api/research/runs/plan', async ({ request }) => {
      requests++;
      const input = (await request.json()) as ResearchPlanInput;
      await pending;
      return HttpResponse.json(areaPreview(input));
    }),
  );
  const { result } = renderHook(() => useAreaResearch(researchArea, null, defaultProfile), {
    wrapper: MemoryRouter,
  });
  let first: Promise<void> | undefined;
  act(() => {
    first = result.current.checkSources();
    void result.current.checkSources();
  });
  await waitFor(() => expect(requests).toBe(1));
  expect(result.current.prepareHandoff()).toBe(false);
  await act(() => result.current.checkSources());
  expect(requests).toBe(1);
  await act(async () => {
    finish();
    await first;
  });
  expect(result.current.preview).not.toBeNull();
});
