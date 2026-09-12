import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach, vi } from 'vitest';

// Cold lazy routes and MSW round trips under coverage can exceed four seconds.
// Keep async assertions inside the suite's 15-second per-test budget.
configure({ asyncUtilTimeout: 10_000 });

import { initialAuthState, useAuthStore } from '@/stores/auth';
import { initialCapabilitiesState, useCapabilitiesStore } from '@/stores/capabilities';
import { initialCountriesState, useCountriesStore } from '@/stores/countries';
import { initialEventsState, useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import { DEFAULT_BASE_LAYER } from '@/lib/map/baseLayers';

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
    transparent?: boolean;
  }
  function EvilEyeStub(props: StubProps) {
    return React.createElement('div', {
      'data-testid': 'evil-eye',
      'data-paused': String(props.paused ?? false),
      'data-max-fps': String(props.maxFps ?? 'none'),
      'data-flame-speed': String(props.flameSpeed ?? 1),
      'data-pupil-follow': String(props.pupilFollow ?? 1),
      'data-background': props.backgroundColor ?? '#000000',
      'data-transparent': String(props.transparent ?? false),
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
  useGlobeStore.setState({
    mode: 'globe',
    baseLayer: DEFAULT_BASE_LAYER,
    terminator: false,
    lite: false,
    interference: false,
  });
  localStorage.clear();
  useCapabilitiesStore.setState({ ...initialCapabilitiesState });
  useEventsStore.setState({ ...initialEventsState });
  useCountriesStore.setState({ ...initialCountriesState });
  clearCookies();
  resetVisibility();
});

afterAll(() => {
  server.close();
});
