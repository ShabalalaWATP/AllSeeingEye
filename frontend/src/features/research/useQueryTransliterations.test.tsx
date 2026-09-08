import { act, renderHook } from '@testing-library/react';
import { expect, it } from 'vitest';
import { useQueryTransliterations } from './useQueryTransliterations';

it('requires exact aligned originals, named methods and case-sensitive ISO script codes', () => {
  const { result } = renderHook(() => useQueryTransliterations(['en'], ['Original']));
  expect(result.current.variants).toEqual([]);
  act(() =>
    result.current.update('en', {
      original: 'Original',
      transformed: 'Rendered',
      method: 'Operator convention',
      sourceScript: 'Arab',
      targetScript: 'Latn',
    }),
  );
  expect(result.current.error).toBeNull();
  for (const change of [
    { original: 'Different' },
    { original: 'Original', transformed: 'First\nSecond' },
    { transformed: 'Rendered', method: ' ' },
    { method: 'Operator convention', sourceScript: 'arab' },
    { sourceScript: 'Arab', targetScript: 'LATN' },
  ]) {
    act(() => result.current.update('en', change));
    expect(result.current.error).toMatch(/exact original search term/);
  }
  act(() => result.current.update('en', { targetScript: 'Latn' }));
  expect(result.current.error).toBeNull();
});
it('does not execute retained drafts for deselected languages or without original query terms', () => {
  const { result, rerender } = renderHook<
    ReturnType<typeof useQueryTransliterations>,
    { languages: string[]; terms: string[] | null }
  >(
    ({ languages, terms }: { languages: string[]; terms: string[] | null }) =>
      useQueryTransliterations(languages, terms),
    {
      initialProps: { languages: ['en'], terms: null },
    },
  );
  act(() =>
    result.current.update('en', {
      original: 'Original',
      transformed: 'Rendered',
      method: 'Operator convention',
      sourceScript: 'Arab',
      targetScript: 'Latn',
    }),
  );
  expect(result.current.error).not.toBeNull();
  rerender({ languages: [], terms: ['Original'] });
  expect(result.current.variants).toEqual([]);
  rerender({ languages: ['en'], terms: ['Original'] });
  expect(result.current.error).toBeNull();
  expect(result.current.variants[0]?.terms).toEqual(['Rendered']);
});

it.each([
  { method: 'Operator convention' },
  { sourceScript: 'Arab' },
  { targetScript: 'Latn' },
  { transformed: 'Rendered' },
])(
  'keeps an incomplete explicit draft visible for validation instead of silently dropping it',
  (draft) => {
    const { result } = renderHook(() => useQueryTransliterations(['en'], ['Original']));
    act(() => result.current.update('en', draft));
    expect(result.current.variants).toHaveLength(1);
    expect(result.current.error).toMatch(/Link each transliterated phrase/);
  },
);
