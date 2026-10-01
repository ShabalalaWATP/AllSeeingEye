import { renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

import { useGlobeInterference } from './useGlobeInterference';

const polled = vi.hoisted(() => [] as boolean[]);
const cells = vi.hoisted(() => [
  { lon: 1, lat: 1, size: 1, level: 'red', good: 4, bad: 6 },
  { lon: 2, lat: 2, size: 1, level: 'green', good: 9, bad: 1 },
]);
vi.mock('./useInterference', () => ({
  useInterference: (enabled: boolean) => {
    polled.push(enabled);
    return { cells, receivedAt: 0, updated_at: null };
  },
}));

it('polls only when enabled and expires the whole snapshot with the shared clock', () => {
  const { result, rerender } = renderHook(
    ({ enabled, now }) => useGlobeInterference(enabled, now),
    {
      initialProps: { enabled: true, now: 60_000 },
    },
  );
  expect(result.current.filters.filtered).toEqual([cells[0]]);
  expect(result.current.filters.stale).toBe(false);
  rerender({ enabled: false, now: 15 * 60_000 });
  expect(polled).toEqual([true, false]);
  expect(result.current.filters.expired).toBe(true);
  expect(result.current.filters.filtered).toEqual([]);
});
