import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, expect, it } from 'vitest';

import { applySession } from '@/test/render';
import { useAuthStore } from '@/stores/auth';

import {
  clearDraft,
  draftCount,
  hasDraft,
  readDraft,
  useDraftState,
  useHasDraft,
} from './formDrafts';
import { useUnloadWarning } from './hooks/useUnloadWarning';
import { invalidateWorkspaceAccess } from './workspaceAccess';

beforeEach(() => applySession('user'));
afterEach(() => clearDraft('test-form'));

it('restores edited fields for the same account and form after a remount', () => {
  const first = renderHook(() => useDraftState('test-form', 'question', ''));
  expect(hasDraft('test-form')).toBe(false);
  act(() => first.result.current[1]('Where is the convoy?'));
  act(() => first.result.current[1]((value) => `${value} Today?`));
  first.unmount();
  const second = renderHook(() => useDraftState('test-form', 'question', ''));
  expect(second.result.current[0]).toBe('Where is the convoy? Today?');
  expect(hasDraft('test-form')).toBe(true);
  const other = renderHook(() => useDraftState('other-form', 'question', 'initial'));
  expect(other.result.current[0]).toBe('initial');
});

it('never creates a draft for an untouched form or a form without a draft key', () => {
  renderHook(() => useDraftState('test-form', 'question', 'default'));
  const unkeyed = renderHook(() => useDraftState(null, 'question', ''));
  act(() => unkeyed.result.current[1]('Not kept'));
  expect(hasDraft('test-form')).toBe(false);
  expect(readDraft('test-form')).toBeUndefined();
});

it.each([
  ['sign-out', () => useAuthStore.getState().clearSession()],
  ['access change', () => invalidateWorkspaceAccess()],
  ['account change', () => applySession('admin')],
])('clears every draft on %s', (_name, change) => {
  const view = renderHook(() => useDraftState('test-form', 'question', ''));
  act(() => view.result.current[1]('Private question'));
  view.unmount();
  expect(draftCount()).toBe(1);
  act(() => change());
  expect(draftCount()).toBe(0);
  applySession('user');
  expect(hasDraft('test-form')).toBe(false);
  expect(renderHook(() => useDraftState('test-form', 'question', '')).result.current[0]).toBe('');
});

it('clears one form explicitly, for example after a successful submission', () => {
  const view = renderHook(() => useDraftState('test-form', 'name', ''));
  act(() => view.result.current[1]('Weekly watch'));
  clearDraft('test-form');
  expect(hasDraft('test-form')).toBe(false);
});

it('reports unsent work reactively and warns before a reload until it is cleared', () => {
  const presence = renderHook(() => {
    const dirty = useHasDraft('test-form');
    useUnloadWarning(dirty);
    return dirty;
  });
  const unload = () => {
    const event = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(event);
    return event.defaultPrevented;
  };
  expect(presence.result.current).toBe(false);
  expect(unload()).toBe(false);
  const view = renderHook(() => useDraftState('test-form', 'name', ''));
  act(() => view.result.current[1]('Unsent'));
  expect(presence.result.current).toBe(true);
  expect(unload()).toBe(true);
  act(() => clearDraft('test-form'));
  expect(presence.result.current).toBe(false);
  expect(unload()).toBe(false);
});
