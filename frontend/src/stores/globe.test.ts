import { describe, expect, it } from 'vitest';

import { useGlobeStore } from './globe';

describe('globe store', () => {
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
