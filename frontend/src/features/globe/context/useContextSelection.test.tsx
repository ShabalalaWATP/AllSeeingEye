import { act, renderHook } from '@testing-library/react';
import { expect, it } from 'vitest';
import { applySession } from '@/test/render';
import { liveEvent } from '@/test/fixtures';
import { useContextSelection } from './useContextSelection';

it('keeps unlocated context inspectable without fabricating a marker and clears across batched sessions', () => {
  applySession('user');
  const { result, rerender } = renderHook(
    ({ country, picking }) => useContextSelection(country, picking),
    { initialProps: { country: null as string | null, picking: false } },
  );
  const unlocated = liveEvent({ point: null });
  act(() => result.current.choose(unlocated));
  expect(result.current.event).toBe(unlocated);
  expect(result.current.layers).toEqual([]);
  act(() => {
    applySession('anonymous');
    applySession('user');
  });
  expect(result.current.event).toBeNull();
  act(() => result.current.choose(liveEvent()));
  expect(result.current.layers).toHaveLength(1);
  rerender({ country: 'GB', picking: false });
  expect(result.current.event).toBeNull();
  rerender({ country: null, picking: true });
  act(() => result.current.choose(unlocated));
  expect(result.current.event).toBeNull();
});
