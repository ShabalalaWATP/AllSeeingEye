import { RF_ANTENNA_DEFAULTS } from '@/lib/map/rfAntenna';
import type { RfDraft } from '@/lib/map/rfDraft';
export function RfAntennaControls({
  draft,
  onChange,
}: {
  draft: RfDraft;
  onChange: (draft: RfDraft) => void;
}) {
  const antenna = draft.antenna ?? RF_ANTENNA_DEFAULTS;
  return (
    <details>
      <summary>Directional link assumptions</summary>
      <label className="flex gap-2 text-xs">
        <input
          type="checkbox"
          checked={antenna.enabled}
          onChange={(event) =>
            onChange({ ...draft, antenna: { ...antenna, enabled: event.target.checked } })
          }
        />
        Use an idealised horizontal antenna pattern
      </label>
      {antenna.enabled && (
        <div className="rf-field-grid">
          {(
            [
              ['transmitterBearing', 'TX bearing (° true)', 0, 360],
              ['receiverBearing', 'RX bearing (° true)', 0, 360],
              ['beamwidth', 'Full -3 dB beamwidth (°)', 1, 180],
              ['maximumAttenuation', 'Maximum off-axis attenuation (dB)', 0, 60],
            ] as const
          ).map(([key, label, min, max]) => (
            <label className="rf-field" key={key}>
              <span>{label}</span>
              <input
                type="number"
                value={antenna[key]}
                min={min}
                max={max}
                onChange={(event) =>
                  onChange({ ...draft, antenna: { ...antenna, [key]: event.target.value } })
                }
              />
            </label>
          ))}
        </div>
      )}
      <p className="rf-help">
        Terrain and free-space receiver links only. Both sites use the selected horizontal beamwidth
        and attenuation cap. The idealised parabolic cut reduces gain away from each bearing; it
        does not model vertical tilt, polarisation or measured antenna lobes. Area and HF models
        require this option to be off.
      </p>
    </details>
  );
}
