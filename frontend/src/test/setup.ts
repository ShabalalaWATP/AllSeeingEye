import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach, vi } from 'vitest';

// Lazy route chunks and MSW round trips can exceed the 1 s default on a busy machine.
configure({ asyncUtilTimeout: 4000 });

import { initialAuthState, useAuthStore } from '@/stores/auth';
import { initialCountriesState, useCountriesStore } from '@/stores/countries';
import { initialEventsState, useEventsStore } from '@/stores/events';
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
  useEventsStore.setState({ ...initialEventsState });
  useCountriesStore.setState({ ...initialCountriesState });
  clearCookies();
  resetVisibility();
});

afterAll(() => {
  server.close();
});
