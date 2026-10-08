import { act, renderHook } from '@testing-library/react';
import { expect, it } from 'vitest';

import { useKeyedConsent } from './useKeyedConsent';

it('withdraws consent when the key changes, even if the old key returns', () => {
  const { result, rerender } = renderHook(({ key }) => useKeyedConsent(key), {
    initialProps: { key: 'plan-a' },
  });
  expect(result.current[0]).toBe(false);
  act(() => result.current[1](true));
  expect(result.current[0]).toBe(true);
  rerender({ key: 'plan-a' });
  expect(result.current[0]).toBe(true);
  rerender({ key: 'plan-b' });
  expect(result.current[0]).toBe(false);
  rerender({ key: 'plan-a' });
  expect(result.current[0]).toBe(false);
  act(() => result.current[1](true));
  act(() => result.current[1](false));
  expect(result.current[0]).toBe(false);
});
