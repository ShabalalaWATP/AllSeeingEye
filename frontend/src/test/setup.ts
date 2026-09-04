import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach, vi } from 'vitest';

import { initialAuthState, useAuthStore } from '@/stores/auth';
import { useGlobeStore } from '@/stores/globe';

import { clearCookies, mockMatchMedia, mockWebGl2, resetVisibility } from './env';
import { server } from './server';

// jsdom has no WebGL, so the vendored Evil Eye is replaced by a stub that
// exposes the props the wrappers pass to it.
vi.mock('../components/brand/EvilEye', async () => {
  const React = await import('react');
  interface StubProps {
    paused?: boolean;
    maxFps?: number;
    flameSpeed?: number;
    pupilFollow?: number;
    backgroundColor?: string;
  }
  function EvilEyeStub(props: StubProps) {
    return React.createElement('div', {
      'data-testid': 'evil-eye',
      'data-paused': String(props.paused ?? false),
      'data-max-fps': String(props.maxFps ?? 'none'),
      'data-flame-speed': String(props.flameSpeed ?? 1),
      'data-pupil-follow': String(props.pupilFollow ?? 1),
      'data-background': props.backgroundColor ?? '#000000',
    });
  }
  return { default: EvilEyeStub };
});

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});

beforeEach(() => {
  mockMatchMedia(false);
  mockWebGl2(false);
});

afterEach(() => {
  server.resetHandlers();
  cleanup();
  useAuthStore.setState(initialAuthState);
  useGlobeStore.setState({ mode: 'globe' });
  clearCookies();
  resetVisibility();
});

afterAll(() => {
  server.close();
});
