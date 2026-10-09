import { useAuthStore } from '@/stores/auth';
import { createMapLibreEngine } from '@/lib/map/MapLibreEngine';
import type { EngineOptions } from '@/lib/map/MapEngine';
import { mapSourceAllowed } from '@/lib/map/sourcePolicy';

/** The engine's origin check keeps session tokens restricted to our own tile proxy. */
export const createEngine = (options: EngineOptions = {}) =>
  createMapLibreEngine({
    ...options, sourceAllowed: mapSourceAllowed,
    authHeader: () => useAuthStore.getState().accessToken,
  });
