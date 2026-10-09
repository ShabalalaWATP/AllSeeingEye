import { act, renderHook } from '@testing-library/react';
import { expect, it } from 'vitest';

import { useRevealedLinks } from './useRevealedLinks';

it('keeps distinct links newest first and dismisses one at a time', () => {
  const { result } = renderHook(() => useRevealedLinks());
  act(() => result.current.reveal({ title: 'A', link: 'https://a', expiresAt: '2026-01-01' }));
  act(() => result.current.reveal({ title: 'B', link: 'https://b', expiresAt: '2026-01-01' }));
  expect(result.current.links.map((item) => item.title)).toEqual(['B', 'A']);
  act(() => result.current.reveal({ title: 'A', link: 'https://a2', expiresAt: '2026-01-02' }));
  expect(result.current.links.map((item) => item.link)).toEqual(['https://a2', 'https://b']);
  const first = result.current.links[0];
  act(() => result.current.dismiss(first?.key ?? -1));
  expect(result.current.links.map((item) => item.title)).toEqual(['B']);
});
