/** Explicit planning assumptions, separate from physical received-power predictions. */
export interface RfEngineeringSettings {
  reserveDb: number;
  obstacleHeightM: number;
  earthFactor: number;
}

export const RF_ENGINEERING_FIELDS = [
  { key: 'reserveDb', label: 'Planning reserve (dB)', min: 0, max: 60, step: 1 },
  { key: 'obstacleHeightM', label: 'Assumed obstacle height (m)', min: 0, max: 100, step: 1 },
  { key: 'earthFactor', label: 'Effective Earth factor (k)', min: 0.667, max: 2, step: 0.01 },
] as const;

/** The default reserve is an editable allowance, not a calibrated reliability percentage. */
export const RF_ENGINEERING_DRAFT_DEFAULTS = {
  reserveDb: '10',
  obstacleHeightM: '0',
  earthFactor: String(4 / 3),
};
export type RfEngineeringDraft = typeof RF_ENGINEERING_DRAFT_DEFAULTS;

export function validateRfEngineering(settings: RfEngineeringSettings): RfEngineeringSettings {
  for (const { key, label, min, max } of RF_ENGINEERING_FIELDS) {
    if (!Number.isFinite(settings[key]) || settings[key] < min || settings[key] > max)
      throw new Error(`${label}: enter a value from ${min} to ${max}.`);
  }
  return settings;
}

export function parseRfEngineering(
  draft?: Partial<RfEngineeringDraft>,
  mode: 'terrain' | 'free-space' | 'hf-groundwave' = 'terrain',
): RfEngineeringSettings {
  const values = { ...RF_ENGINEERING_DRAFT_DEFAULTS, ...draft };
  // Hidden, irrelevant scenario edits must not block a different model.
  if (mode !== 'terrain') values.obstacleHeightM = '0';
  if (mode === 'hf-groundwave') values.earthFactor = RF_ENGINEERING_DRAFT_DEFAULTS.earthFactor;
  return validateRfEngineering(
    Object.fromEntries(
      Object.entries(values).map(([key, value]) => [key, value.trim() ? Number(value) : NaN]),
    ) as unknown as RfEngineeringSettings,
  );
}

/** Existing equation callers retain zero reserve unless they opt into a planning scenario. */
export const RF_PHYSICAL_REFERENCE: RfEngineeringSettings = {
  reserveDb: 0,
  obstacleHeightM: 0,
  earthFactor: 4 / 3,
};
