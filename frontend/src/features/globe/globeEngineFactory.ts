import { useAuthStore } from '@/stores/auth';
import { createMapLibreEngine } from '@/lib/map/MapLibreEngine';
import type { EngineOptions } from '@/lib/map/MapEngine';

/** The engine's origin check keeps session tokens restricted to our own tile proxy. */
export const createEngine = (options: EngineOptions = {}) =>
  createMapLibreEngine({ ...options, authHeader: () => useAuthStore.getState().accessToken });
