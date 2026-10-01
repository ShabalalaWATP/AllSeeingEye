import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { expect, it } from 'vitest';

import { MAP_GUIDE_PANEL } from '@/lib/mapLayerDirectory';

import { useGlobePanelRoute } from './useGlobePanelRoute';

function routed(path: string) {
  let router: ReturnType<typeof createMemoryRouter> | null = null;
  const wrapper = ({ children }: { children: ReactNode }) => {
    router ??= createMemoryRouter([{ path: '/', element: children }], { initialEntries: [path] });
    return <RouterProvider router={router} />;
  };
  const view = renderHook(useGlobePanelRoute, { wrapper });
  return { ...view, router: () => router! };
}

it('reads a requested panel, accepting the short id for the guide', () => {
  const { result } = routed('/?panel=guide');
  expect(result.current.requestedPanel).toBe(MAP_GUIDE_PANEL);
  expect(result.current.showPanel.current).toBeNull();
});

it('records user navigation with canonical ids and keeps other parameters', () => {
  const { result, router } = routed('/?view=abc');
  act(() => result.current.onPanelChange(MAP_GUIDE_PANEL));
  expect(router().state.location.search).toBe('?view=abc&panel=guide');
  expect(result.current.requestedPanel).toBe(MAP_GUIDE_PANEL);
  const key = result.current.requestKey;

  act(() => result.current.onPanelChange(null));
  expect(router().state.location.search).toBe('?view=abc');
  expect(result.current.requestedPanel).toBeNull();
  expect(result.current.requestKey).not.toBe(key);
});

it('does not add a history entry when the panel is unchanged', () => {
  const { result, router } = routed('/?panel=guide');
  const key = router().state.location.key;
  act(() => result.current.onPanelChange(MAP_GUIDE_PANEL));
  expect(router().state.location.key).toBe(key);
});

it('keeps an unknown label as given so a later directory entry can resolve it', () => {
  const { result, router } = routed('/');
  act(() => result.current.onPanelChange('Unlisted tool'));
  expect(new URLSearchParams(router().state.location.search).get('panel')).toBe('Unlisted tool');
});
