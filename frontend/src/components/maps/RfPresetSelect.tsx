import { RF_PRESETS } from '@/lib/map/rfPresets';
import type { RfPreset } from '@/lib/map/rfPresets';

const GROUPS = [
  { id: 'bowman', label: 'Bowman planning scenarios' },
  { id: 'military', label: 'Other military radios' },
  { id: undefined, label: 'General radio examples' },
] as const;

export function RfPresetSelect({
  presetId,
  onSelect,
}: {
  presetId: string;
  onSelect: (preset: RfPreset) => void;
}) {
  const selected = RF_PRESETS.find((item) => item.id === presetId);
  return (
    <div className="rf-preset">
      <label className="rf-field">
        Radio preset
        <select
          value={presetId}
          onChange={(event) => {
            const preset = RF_PRESETS.find((item) => item.id === event.target.value);
            if (preset) onSelect(preset);
          }}
        >
          <option value="custom">Custom radio link</option>
          {GROUPS.map((group) => (
            <optgroup key={group.label} label={group.label}>
              {RF_PRESETS.filter((item) => item.id !== 'custom' && item.group === group.id).map(
                (item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ),
              )}
            </optgroup>
          ))}
        </select>
      </label>
      {selected?.basis && (
        <p className="rf-preset-basis">
          {selected.basis === 'published'
            ? 'Published equipment data with editable planning inputs'
            : 'Illustrative configuration: verify your radio variant'}
        </p>
      )}
      <details className="rf-disclosure rf-preset-details">
        <summary>Preset details &amp; assumptions</summary>
        <div className="rf-disclosure-body">
          {selected?.specification && (
            <dl aria-label="Published radio specifications" className="rf-specifications">
              <dt className="text-muted">Band</dt>
              <dd>{selected.specification.band}</dd>
              <dt className="text-muted">RF output</dt>
              <dd>{selected.specification.output}</dd>
            </dl>
          )}
          <p className="rf-help">{selected?.note}</p>
          <p className="rf-help">
            Selected frequencies, antenna heights, gains, losses and receiver sensitivity are
            editable examples. Presets do not establish current network settings or guaranteed
            range.
          </p>
        </div>
      </details>
    </div>
  );
}
