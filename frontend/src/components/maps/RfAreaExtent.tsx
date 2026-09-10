import { useId } from 'react';
import { RF_ENVIRONMENT_DEFAULTS, type RfDraft } from '@/lib/map/rfDraft';
import type { RfInputs } from '@/lib/map/rfPlanning';
import { resolveRfMode, rfStudyRadius } from '@/lib/map/rfAutomation';

export function RfAreaExtent({
  draft,
  input,
  onChange,
}: {
  draft: RfDraft;
  input: RfInputs;
  onChange: (draft: RfDraft) => void;
}) {
  const id = useId();
  const automatic = draft.radiusMode === 'automatic';
  const mode = resolveRfMode(draft);
  const env = { ...RF_ENVIRONMENT_DEFAULTS, ...draft.environment };
  let radius: number | null = null;
  try {
    radius = rfStudyRadius(input, draft);
  } catch {
    /* Incomplete input is explained by the form. */
  }
  return (
    <div className="rf-area-extent">
      <label className="rf-auto-toggle" htmlFor={id}>
        <input
          id={id}
          type="checkbox"
          className="rf-checkbox"
          checked={automatic}
          onChange={(event) =>
            onChange({ ...draft, radiusMode: event.target.checked ? 'automatic' : 'manual' })
          }
        />
        Choose analysis area automatically
      </label>
      {!automatic && (
        <label className="rf-field">
          Area to analyse (km from transmitter)
          <input
            type="number"
            step="any"
            min={mode === 'terrain' ? 1 : 2}
            max={mode === 'terrain' ? 50 : 200}
            value={env.radiusKm}
            onChange={(event) =>
              onChange({ ...draft, environment: { ...env, radiusKm: event.target.value } })
            }
          />
        </label>
      )}
      <p className="rf-help">
        {automatic && radius !== null
          ? mode === 'terrain'
            ? `Starts with ${radius.toFixed(1)} km around the transmitter and can refine the sampled area once.`
            : `Checks the groundwave model out to ${radius.toFixed(0)} km.`
          : 'This sets the area examined, not the distance your signal is guaranteed to reach.'}
      </p>
    </div>
  );
}
