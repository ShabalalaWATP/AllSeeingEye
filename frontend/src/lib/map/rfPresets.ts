import { RF_GENERAL_PRESETS } from './rfGeneralPresets';
import { RF_BOWMAN_PRESETS } from './rfBowmanPresets';
import { RF_MILITARY_PRESETS } from './rfMilitaryPresets';
import type { RfPreset } from './rfPresetTypes';
export type { RfPreset } from './rfPresetTypes';
export { BOWMAN_REFERENCES } from './rfBowmanReferences';

export const RF_PRESETS: readonly RfPreset[] = [
  ...RF_GENERAL_PRESETS,
  ...RF_BOWMAN_PRESETS,
  ...RF_MILITARY_PRESETS,
];
