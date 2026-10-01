import { renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

import { useGlobeEvents } from './useGlobeEvents';

const order = vi.hoisted(() => [] as string[]);
vi.mock('./useLiveEvents', () => ({ useLiveEvents: () => order.push('stream') }));
vi.mock('./useDashboardEvents', () => ({
  useDashboardEvents: (now: number) => {
    order.push(`scope:${now}`);
    return { now };
  },
}));

it('subscribes before deriving the event scope and returns that scope unchanged', () => {
  const { result, rerender } = renderHook(({ now }) => useGlobeEvents(now), {
    initialProps: { now: 1 },
  });
  rerender({ now: 2 });
  expect(order).toEqual(['stream', 'scope:1', 'stream', 'scope:2']);
  expect(result.current).toEqual({ now: 2 });
});
