import { DEFAULT_RF_INPUTS } from './rfPlanning';
import type { RfInputs } from './rfPlanning';

export type RfPropagation = 'terrain' | 'free-space' | 'hf-groundwave' | 'hf-skywave';
export const RF_ENVIRONMENT_DEFAULTS = {
  radiusKm: '25',
  conductivitySm: '0.005',
  permittivity: '15',
  refractivity: '301',
  criticalFrequencyMHz: '5',
  virtualHeightKm: '300',
  minElevationDeg: '10',
  maxElevationDeg: '80',
};
export type RfEnvironment = typeof RF_ENVIRONMENT_DEFAULTS;

/** In-memory form strings preserve incomplete edits when the tool panel closes. */
export interface RfDraft {
  values: Record<keyof RfInputs, string>;
  presetId: string;
  propagation?: RfPropagation;
  environment?: RfEnvironment;
}

export function createRfDraft(input: RfInputs = DEFAULT_RF_INPUTS, presetId = 'custom'): RfDraft {
  return {
    values: Object.fromEntries(
      Object.entries(input).map(([key, value]) => [key, String(value)]),
    ) as RfDraft['values'],
    presetId,
    propagation: 'terrain',
    environment: { ...RF_ENVIRONMENT_DEFAULTS },
  };
}
