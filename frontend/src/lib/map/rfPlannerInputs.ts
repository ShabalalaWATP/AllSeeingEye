import type { RfDraft } from './rfDraft';
import type { RfInputs } from './rfPlanning';
import type { Position } from './geoJsonTypes';
import { directionalRfInputs } from './rfAntenna';
import { resolveRfMode } from './rfAutomation';
import { measure } from './measurements';
export function rfPlannerInputs(
  draft: RfDraft,
  origin: Position | null,
  receiver: Position | null,
): { input: RfInputs; error: string | null } {
  let input = Object.fromEntries(
    Object.entries(draft.values).map(([key, value]) => [key, value.trim() ? Number(value) : NaN]),
  ) as unknown as RfInputs;
  const mode = resolveRfMode(draft);
  if (origin && receiver) input.distanceKm = measure([origin, receiver], 'distance').metres / 1000;
  try {
    if (draft.antenna?.enabled) {
      if (!origin || !receiver || (mode !== 'terrain' && mode !== 'free-space'))
        throw new Error('Directional assumptions require a terrain or free-space receiver link.');
      input = directionalRfInputs(input, origin, receiver, draft.antenna);
    }
    return { input, error: null };
  } catch (error) {
    return { input, error: error instanceof Error ? error.message : 'Check antenna assumptions.' };
  }
}
