import { describe, expect, it } from 'vitest';

import { GLOBE_PREFS_KEY, useGlobeStore } from './globe';

describe('globe store', () => {
  it('does not restore previously enabled overlays, but preserves valid display preferences', async () => {
    localStorage.setItem(
      GLOBE_PREFS_KEY,
      JSON.stringify({
        state: {
          baseLayer: 'satellite',
          lite: true,
          terminator: true,
          interference: true,
          mode: 'map',
        },
        version: 0,
      }),
    );
    await useGlobeStore.persist.rehydrate();
    expect(useGlobeStore.getState()).toMatchObject({
      baseLayer: 'satellite',
      lite: true,
      terminator: false,
      interference: false,
      mode: 'globe',
    });
    localStorage.setItem(
      GLOBE_PREFS_KEY,
      JSON.stringify({ state: { baseLayer: 'invalid', lite: 'yes' }, version: 0 }),
    );
    await useGlobeStore.persist.rehydrate();
    expect(useGlobeStore.getState()).toMatchObject({ baseLayer: 'satellite', lite: true });
  });
  it('defaults to the globe and toggles to the map and back', () => {
    expect(useGlobeStore.getState().mode).toBe('globe');
    useGlobeStore.getState().toggleMode();
    expect(useGlobeStore.getState().mode).toBe('map');
    useGlobeStore.getState().toggleMode();
    expect(useGlobeStore.getState().mode).toBe('globe');
    useGlobeStore.getState().setMode('map');
    expect(useGlobeStore.getState().mode).toBe('map');
  });
});
