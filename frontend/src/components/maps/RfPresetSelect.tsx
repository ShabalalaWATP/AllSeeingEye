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
    <div className="space-y-2">
      <label className="block text-muted">
        Radio preset
        <select
          value={presetId}
          onChange={(event) => {
            const preset = RF_PRESETS.find((item) => item.id === event.target.value);
            if (preset) onSelect(preset);
          }}
          className="mt-1 min-h-10 w-full rounded border border-line bg-ground px-2 text-text"
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
        <p className="text-cyan">
          {selected.basis === 'published'
            ? 'Published equipment data with editable planning inputs'
            : 'Illustrative configuration: verify your radio variant'}
        </p>
      )}
      {selected?.specification && (
        <dl
          aria-label="Published radio specifications"
          className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 border-l border-line pl-3"
        >
          <dt className="text-muted">Band</dt>
          <dd>{selected.specification.band}</dd>
          <dt className="text-muted">RF output</dt>
          <dd>{selected.specification.output}</dd>
        </dl>
      )}
      <p className="text-muted">{selected?.note}</p>
      <p className="text-muted">
        Selected frequencies, antenna heights, gains, losses and receiver sensitivity are editable
        examples. Presets do not establish current network settings or guaranteed range.
      </p>
    </div>
  );
}
