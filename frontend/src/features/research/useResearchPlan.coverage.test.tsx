import { act, renderHook } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/researchPlan';
import { useResearchPlan, type PlanScope } from './useResearchPlan';

const scope: PlanScope = {
  question: 'What changed?',
  windowHours: '24',
  languages: ['en'],
  mode: 'quick',
  focus: 'general',
  subject: '',
};
function answer(input: api.ResearchPlanInput) {
  return api.previewSchema.parse({
    ...input,
    time_basis: input.time_basis ?? 'publication',
    subject: input.subject ?? null,
    country_iso: null,
    tasks: [],
    request_limit: 8,
    seconds_limit: 20,
    item_limit: 50,
    policy_version: 'fixture',
    model_calls: 0,
    translation_calls: 0,
    replans: 0,
  });
}
beforeEach(() => {
  vi.spyOn(api, 'previewResearchPlan').mockImplementation((input) =>
    Promise.resolve(answer(input)),
  );
});
const mount = (changes: Partial<PlanScope> = {}) =>
  renderHook(() => useResearchPlan({ ...scope, ...changes }));

it('preserves a legacy single-country scope in the preview request', async () => {
  const { result } = mount({ country: 'GB' });
  await act(async () => result.current.preview());
  expect(api.previewResearchPlan).toHaveBeenCalledWith(
    expect.objectContaining({ countries: ['GB'] }),
    expect.any(AbortSignal),
  );
  expect(result.current.current).toBe(true);
});

it.each([
  [{ question: ' ' }, 'Enter a question'],
  [{ question: 'x'.repeat(1001) }, 'Enter a question'],
  [{ languages: [] }, 'select at least one'],
  [{ countries: ['GB', 'GB'] }, 'distinct countries'],
  [{ countries: ['gb'] }, 'distinct countries'],
  [{ countries: ['GB', 'US', 'FR', 'DE', 'ES', 'IT', 'CA', 'AU', 'NZ'] }, 'distinct countries'],
  [{ windowHours: '0' }, 'valid search period'],
  [{ windowHours: '1.5' }, 'valid search period'],
  [{ windowHours: String(730 * 24 + 1) }, 'valid search period'],
  [{ dates: { since: 'invalid', until: '2026-01-01T00:00:00Z' } }, 'date'],
  [{ focus: 'document', webSearch: true }, 'private attachments'],
  [{ history: { since: '2020-01-01', until: '2021-01-01', projectId: 'abc' } }, 'project ID'],
  [{ history: { since: '2020-01-01', until: '2019-01-01' } }, 'valid project years'],
  [{ history: { since: 'invalid', until: '2021-01-01' } }, 'valid project years'],
  [{ history: { since: '1980-01-01', until: '2021-01-01' } }, 'at most 30 years'],
] satisfies [Partial<PlanScope>, string][])(
  'refuses invalid scope %j without requesting a preview',
  async (changes, expected) => {
    const { result } = mount(changes);
    await act(async () => result.current.preview());
    expect(result.current.error?.toLowerCase()).toContain(expected.toLowerCase());
    expect(api.previewResearchPlan).not.toHaveBeenCalled();
  },
);

it.each([
  Array.from({ length: 13 }, (_, i) => `term${i}`).join('\n'),
  'x'.repeat(301),
  Array(4).fill('x'.repeat(260)).join('\n'),
])('validates explicit term budgets before preview', async (terms) => {
  const { result } = mount();
  act(() => {
    result.current.setCustomTerms(true);
    result.current.setTermsText(terms);
  });
  await act(async () => result.current.preview());
  expect(result.current.error).toContain('Use up to 12 terms');
  expect(api.previewResearchPlan).not.toHaveBeenCalled();
});

it('requires translations to identify matching originals and rejects malformed transliterations', async () => {
  const { result } = mount();
  act(() => {
    result.current.setCustomTerms(true);
    result.current.setTermsText('Port');
    result.current.setVariantText({ en: 'Harbour' });
    result.current.setVariantOriginalText({ en: 'Other' });
  });
  await act(async () => result.current.preview());
  expect(result.current.error).toContain('exact original search terms');
  act(() => result.current.setVariantOriginalText({ en: 'Port\nPort' }));
  await act(async () => result.current.preview());
  expect(api.previewResearchPlan).not.toHaveBeenCalled();
  act(() => {
    result.current.setVariantOriginalText({ en: 'Port' });
    result.current.transliterations.update('en', { transformed: 'Incomplete' });
  });
  await act(async () => result.current.preview());
  expect(result.current.error).toContain('Link each transliterated phrase');
});

it('caps combined variants even when each individual translation is valid', async () => {
  const languages = ['en', 'fr', 'de', 'es', 'ar', 'ru', 'uk', 'zh', 'fa'];
  const { result } = mount({ languages });
  act(() =>
    result.current.setVariantText(
      Object.fromEntries(languages.map((language) => [language, 'Port'])),
    ),
  );
  await act(async () => result.current.preview());
  expect(result.current.error).toContain('eight translation and transliteration');
  expect(api.previewResearchPlan).not.toHaveBeenCalled();
});

it('blocks incomplete tasks and tasks whose source the operator deselected', async () => {
  const { result } = mount();
  act(() => result.current.tasks.addTask());
  await act(async () => result.current.preview());
  expect(result.current.error).toContain('Choose a source');
  act(() => {
    result.current.tasks.updateTask(result.current.tasks.tasks[0]!.id, {
      source_id: 'wikipedia',
      terms: ['Port'],
    });
    result.current.selectSource('google_news', true);
  });
  await act(async () => result.current.preview());
  expect(result.current.error).toContain('Every additional search needs a selected source');
  expect(api.previewResearchPlan).not.toHaveBeenCalled();
  act(() => result.current.resetSources());
  await act(async () => result.current.preview());
  expect(result.current.current).toBe(true);
  expect(result.current.request).toMatchObject({
    research_planned_tasks: [expect.objectContaining({ source_id: 'wikipedia' })],
  });
});

it('keeps one in-flight preview and ignores results after unmount', async () => {
  let resolve!: (result: Awaited<ReturnType<typeof api.previewResearchPlan>>) => void;
  const pending = new Promise<Awaited<ReturnType<typeof api.previewResearchPlan>>>((done) => {
    resolve = done;
  });
  vi.mocked(api.previewResearchPlan).mockReturnValue(pending);
  const { result, unmount } = mount();
  let request!: Promise<void>;
  act(() => {
    request = result.current.preview();
  });
  expect(result.current.busy).toBe(true);
  await act(async () => result.current.preview());
  expect(api.previewResearchPlan).toHaveBeenCalledOnce();
  const [body, signal] = vi.mocked(api.previewResearchPlan).mock.calls[0]!;
  unmount();
  expect(signal.aborted).toBe(true);
  await act(async () => {
    resolve(answer(body));
    await request;
  });
  expect(result.current.snapshot).toBeNull();
});

it('ignores a late preview failure after unmount', async () => {
  let reject!: (reason: Error) => void;
  vi.mocked(api.previewResearchPlan).mockReturnValue(
    new Promise((_done, fail) => {
      reject = fail;
    }),
  );
  const { result, unmount } = mount();
  let request!: Promise<void>;
  act(() => {
    request = result.current.preview();
  });
  unmount();
  await act(async () => {
    reject(new Error('Late private failure'));
    await request;
  });
  expect(result.current.error).toBeNull();
});
