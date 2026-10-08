import { act, renderHook } from '@testing-library/react';
import { expect, it } from 'vitest';

import { useNumberField } from './useNumberField';

it('keeps typed text while updating the value only from readable numbers', () => {
  const { result } = renderHook(() => useNumberField(10, { min: 1, max: 500, integer: true }));
  expect(result.current).toMatchObject({ value: 10, text: '10' });
  act(() => result.current.type(''));
  expect(result.current).toMatchObject({ value: 10, text: '' });
  act(() => result.current.type('4.6'));
  expect(result.current).toMatchObject({ value: 5, text: '4.6' });
  act(() => result.current.type('-'));
  expect(result.current).toMatchObject({ value: 5, text: '-' });
  act(() => result.current.commit());
  expect(result.current).toMatchObject({ value: 5, text: '5' });
});

it('clamps on entry and on replacement', () => {
  const { result } = renderHook(() => useNumberField(2000, { min: 0, max: 1000 }));
  expect(result.current).toMatchObject({ value: 1000, text: '1000' });
  act(() => result.current.type('0'));
  act(() => result.current.type('-3'));
  expect(result.current.value).toBe(0);
  act(() => result.current.commit());
  expect(result.current.text).toBe('0');
  act(() => result.current.set(2.5));
  expect(result.current).toMatchObject({ value: 2.5, text: '2.5' });
  act(() => result.current.set(5000));
  expect(result.current).toMatchObject({ value: 1000, text: '1000' });
});
