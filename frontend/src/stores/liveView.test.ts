import { beforeEach, expect, it } from 'vitest';

import type { LiveViewState } from '@/lib/liveViews/liveViewState';
import { plainUser } from '@/test/fixtures';
import { useAuthStore } from './auth';
import { useGlobeStore } from './globe';
import { useLiveViewStore } from './liveView';

const view = { version: 1, projection: 'globe' } as LiveViewState;

beforeEach(() => {
  useAuthStore.setState({ user: plainUser, status: 'authenticated' });
  useLiveViewStore.setState({ request: null, playlistId: null, rotationNotice: null });
  localStorage.clear();
});

it('hands over each open once and keeps nothing in browser storage', () => {
  useLiveViewStore.getState().openView(view);
  const request = useLiveViewStore.getState().request;
  expect(request).toMatchObject({ kind: 'view', view });
  useLiveViewStore.getState().consume(-1);
  expect(useLiveViewStore.getState().request).toBe(request);
  if (request) useLiveViewStore.getState().consume(request.nonce);
  expect(useLiveViewStore.getState().request).toBeNull();
  useLiveViewStore.getState().startPlaylist('playlist');
  expect(localStorage.length).toBe(0);
});

it('stops the rotation on sign-out and when the ops room is left', () => {
  useLiveViewStore.getState().startPlaylist('playlist');
  useAuthStore.setState({ user: null, status: 'anonymous' });
  expect(useLiveViewStore.getState()).toMatchObject({ playlistId: null, rotationNotice: null });
  useAuthStore.setState({ user: plainUser, status: 'authenticated' });
  useGlobeStore.setState({ opsRoom: true });
  useLiveViewStore.getState().startPlaylist('playlist');
  useGlobeStore.setState({ opsRoom: false });
  expect(useLiveViewStore.getState().playlistId).toBeNull();
});
