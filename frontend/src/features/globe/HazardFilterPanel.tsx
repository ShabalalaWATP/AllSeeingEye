import { useId } from 'react';
import {
  HAZARD_GROUPS,
  type HazardAlert,
  type HazardGroup,
  type HazardOptions,
  type HazardWindow,
} from '@/lib/hazards';

export function HazardFilterPanel({
  options,
  updateOptions,
  counts,
}: {
  options: HazardOptions;
  updateOptions: (patch: Partial<HazardOptions>) => void;
  counts: Record<HazardGroup, number>;
}) {
  const id = useId();
  const selectClass =
    'mt-1 min-h-10 w-full rounded-lg border border-line bg-panel px-2 text-xs text-main';
  return (
    <section aria-label="Natural hazard filters" className="space-y-3 p-3">
      <p className="text-xs text-muted">
        Natural hazards includes FIRMS detections. The FIRMS switch controls that subset; the
        Natural hazards switch controls the whole group.
      </p>
      <fieldset className="space-y-1">
        <legend className="mb-2 text-xs text-muted">Natural hazards and sensor observations</legend>
        {HAZARD_GROUPS.map((choice) => (
          <label
            key={choice.value}
            className={`flex min-h-10 cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-xs ${options.group === choice.value ? 'border-cyan-400/40 bg-cyan-400/10 text-cyan-200' : 'border-white/10 text-muted hover:bg-white/5'}`}
          >
            <input
              type="radio"
              name={id}
              checked={options.group === choice.value}
              onChange={() => updateOptions({ group: choice.value })}
              className="accent-cyan"
            />
            <span className="flex-1">{choice.label}</span>
            <span className="font-mono tabular-nums">
              {counts[choice.value].toLocaleString()}
              <span className="sr-only"> loaded records</span>
            </span>
          </label>
        ))}
      </fieldset>
      <label className="block text-xs text-muted">
        Reported / acquired within
        <select
          className={selectClass}
          value={options.hours}
          onChange={(event) => updateOptions({ hours: event.target.value as HazardWindow })}
        >
          <option value="all">All loaded times</option>
          <option value="24">24 hours</option>
          <option value="72">3 days</option>
          <option value="168">7 days</option>
        </select>
      </label>
      <label className="block text-xs text-muted">
        Earthquake minimum magnitude
        <select
          className={selectClass}
          value={options.minimumMagnitude}
          onChange={(event) => updateOptions({ minimumMagnitude: Number(event.target.value) })}
        >
          <option value="0">Any magnitude</option>
          {[2, 4, 5, 6, 7].map((value) => (
            <option key={value} value={value}>
              M{value}+
            </option>
          ))}
        </select>
      </label>
      <label className="block text-xs text-muted">
        GDACS impact alert
        <select
          className={selectClass}
          value={options.alert}
          onChange={(event) => updateOptions({ alert: event.target.value as HazardAlert })}
        >
          <option value="all">All alert levels</option>
          <option value="orange_red">Orange and red</option>
          <option value="red">Red only</option>
        </select>
      </label>
      <label className="flex min-h-10 items-center gap-2 text-xs text-muted">
        <input
          type="checkbox"
          className="accent-cyan"
          checked={options.includeUnknown}
          onChange={(event) => updateOptions({ includeUnknown: event.target.checked })}
        />
        Keep records with unknown filter values
      </label>
      <p className="text-[11px] leading-relaxed text-muted">
        Counts are loaded records, not unique disasters. Thermal pixels do not establish a wildfire
        or its cause. FIRMS may be geographically sampled.
      </p>
      <p className="text-[11px] leading-relaxed text-muted">
        Time uses the source report or acquisition date, not necessarily the hazard onset. Magnitude
        applies only to earthquakes with an explicit magnitude; GDACS alert levels apply only to
        GDACS. Other sources keep their own scales.
      </p>
      <button
        type="button"
        className="min-h-10 text-xs text-cyan"
        onClick={() =>
          updateOptions({
            group: 'all',
            hours: 'all',
            minimumMagnitude: 0,
            alert: 'all',
            includeUnknown: true,
          })
        }
      >
        Reset hazard filters
      </button>
    </section>
  );
}
