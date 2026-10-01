import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { MemoryRouter, useLocation } from 'react-router';
import { beforeEach, expect, it, vi } from 'vitest';

import * as api from '@/lib/api/liveViews';
import type { LiveViewState } from '@/lib/liveViews/liveViewState';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useLiveViewStore } from '@/stores/liveView';
import { plainUser } from '@/test/fixtures';
import { useLiveViewOpening } from './useLiveViewOpening';

const view: LiveViewState = {
  version: 1,
  projection: 'map',
  camera: { center: [24, 57], zoom: 5, bearing: 0, pitch: 0 },
  base_layer: 'dark',
  layers: ['aviation'],
  window_hours: 24,
  nation: 'EE',
  filters: {},
  plan_id: null,
};
const opened: Awaited<ReturnType<typeof api.getLiveView>> = {
  view,
  dropped: ['retired layer'],
  document: {
    id: 'saved-view',
    title: 'Baltic',
    kind: 'live_view',
    payload: {},
    revision: 1,
    created_by: plainUser.id,
    team_id: null,
    created_at: '2026-10-01T00:00:00Z',
    updated_at: '2026-10-01T00:00:00Z',
  },
};

function deferred() {
  let resolve!: (value: typeof opened) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<typeof opened>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  useLiveViewStore.getState().reset();
  vi.spyOn(api, 'getLiveView').mockResolvedValue(opened);
});

function mount(path = '/?panel=weather') {
  const apply = vi.fn();
  const controls = { capture: () => view, apply };
  const hook = renderHook(
    () => ({ opening: useLiveViewOpening(controls), search: useLocation().search }),
    {
      wrapper: ({ children }: { children: ReactNode }) => (
        <MemoryRouter initialEntries={[path]}>{children}</MemoryRouter>
      ),
    },
  );
  return { ...hook, apply };
}

it('focuses rotation areas and clears only the rotation focus when a saved view follows', () => {
  const { result, apply } = mount();
  act(() => useLiveViewStore.getState().startPlaylist('wall'));
  act(() => useLiveViewStore.getState().focusArea('port'));
  expect(new URLSearchParams(result.current.search).get('area')).toBe('port');
  expect(useLiveViewStore.getState().request).toBeNull();
  expect(apply).not.toHaveBeenCalled();

  act(() => useLiveViewStore.getState().openView(view));
  expect(apply).toHaveBeenCalledExactlyOnceWith(view);
  expect(new URLSearchParams(result.current.search).has('area')).toBe(false);
  expect(new URLSearchParams(result.current.search).get('panel')).toBe('weather');
  expect(useLiveViewStore.getState().request).toBeNull();
  expect(api.getLiveView).not.toHaveBeenCalled();
});

it('clears a rotating area when the playlist stops while retaining unrelated query state', () => {
  const { result } = mount();
  act(() => useLiveViewStore.getState().startPlaylist('wall'));
  act(() => useLiveViewStore.getState().focusArea('port'));
  expect(new URLSearchParams(result.current.search).get('area')).toBe('port');
  act(() => useLiveViewStore.getState().stopPlaylist());
  expect(result.current.search).toBe('?panel=weather');
});

it('does not erase a manually selected area when opening a view without rotation', () => {
  const { result, apply } = mount('/?area=manual&panel=weather');
  act(() => useLiveViewStore.getState().openView(view));
  expect(apply).toHaveBeenCalledExactlyOnceWith(view);
  expect(new URLSearchParams(result.current.search).get('area')).toBe('manual');
});

it.each(['dismiss', 'access', 'unmount'] as const)(
  'aborts a pending read on %s and ignores a late successful response',
  async (boundary) => {
    const pending = deferred();
    vi.mocked(api.getLiveView).mockReturnValueOnce(pending.promise);
    const { result, unmount, apply } = mount();
    act(() => result.current.opening.openId('saved-view'));
    expect(result.current.opening.notice?.status).toBe('loading');
    const signal = vi.mocked(api.getLiveView).mock.calls[0]![1]!;
    act(() => {
      if (boundary === 'dismiss') result.current.opening.dismiss();
      else if (boundary === 'access') invalidateWorkspaceAccess();
      else unmount();
    });
    expect(signal.aborted).toBe(true);
    await act(async () => {
      pending.resolve(opened);
      await pending.promise;
    });
    expect(apply).not.toHaveBeenCalled();
    if (boundary !== 'unmount') expect(result.current.opening.notice).toBeNull();
  },
);

it('re-reads the same ID and ignores a superseded error while the replacement is loading', async () => {
  const first = deferred();
  const second = deferred();
  vi.mocked(api.getLiveView).mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
  const { result, apply } = mount();
  act(() => result.current.opening.openId('saved-view'));
  const firstSignal = vi.mocked(api.getLiveView).mock.calls[0]![1]!;
  act(() => result.current.opening.openId('saved-view'));
  expect(firstSignal.aborted).toBe(true);
  expect(api.getLiveView).toHaveBeenCalledTimes(2);
  await act(async () => {
    first.reject(new Error('superseded request'));
    await expect(first.promise).rejects.toThrow('superseded request');
  });
  expect(result.current.opening.notice?.status).toBe('loading');
  await act(async () => {
    second.resolve(opened);
    await second.promise;
  });
  expect(apply).toHaveBeenCalledExactlyOnceWith(view);
  expect(result.current.opening.notice).toEqual({
    status: 'opened',
    title: 'Baltic',
    dropped: ['retired layer'],
  });

  const third = deferred();
  vi.mocked(api.getLiveView).mockReturnValueOnce(third.promise);
  act(() => result.current.opening.openId('saved-view'));
  expect(result.current.opening.notice).toEqual({ status: 'loading', title: null, dropped: [] });
  await act(async () => {
    third.resolve(opened);
    await third.promise;
  });
  expect(api.getLiveView).toHaveBeenCalledTimes(3);
  expect(apply).toHaveBeenCalledTimes(2);
});
