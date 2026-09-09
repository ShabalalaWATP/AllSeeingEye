import { DEFAULT_RF_INPUTS } from './rfPlanning';
import type { RfInputs } from './rfPlanning';

/** In-memory form strings preserve incomplete edits when the tool panel closes. */
export interface RfDraft {
  values: Record<keyof RfInputs, string>;
  presetId: string;
}

export function createRfDraft(input: RfInputs = DEFAULT_RF_INPUTS, presetId = 'custom'): RfDraft {
  return {
    values: Object.fromEntries(
      Object.entries(input).map(([key, value]) => [key, String(value)]),
    ) as RfDraft['values'],
    presetId,
  };
}
