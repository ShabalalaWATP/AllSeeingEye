import type { FireKind, FiresOptions } from '@/lib/hazards';

const CHOICES = [
  {
    kind: 'thermal',
    label: 'FIRMS thermal detections',
    note: 'NASA satellite heat observations, shown with a sensor symbol.',
  },
  {
    kind: 'wildfire',
    label: 'Reported wildfires',
    note: 'Wildfire reports from sources such as NASA EONET and GDACS, shown with a flame symbol.',
  },
] as const;

export function FiresFilterPanel({
  options,
  updateOptions,
  counts,
  enabled,
}: {
  options: FiresOptions;
  updateOptions: (patch: Partial<FiresOptions>) => void;
  counts: Record<FireKind | 'all', number>;
  enabled: boolean;
}) {
  return (
    <section aria-label="Fire filters" className="space-y-3 p-3">
      <p className="text-xs text-muted">
        Choose satellite detections, reported wildfires, or both. The Fires switch controls this
        layer independently from Natural hazards.
      </p>
      {!enabled && (
        <p className="rounded-lg border border-amber/20 bg-amber/5 p-3 text-xs text-muted">
          Fires is off. Your selections take effect when you enable its switch.
        </p>
      )}
      <fieldset className="space-y-2">
        <legend className="mb-2 text-xs text-muted">Fire evidence</legend>
        {CHOICES.map(({ kind, label, note }) => (
          <label
            key={kind}
            className={`flex min-h-11 cursor-pointer items-start gap-2 rounded-lg border p-3 text-xs ${options[kind] ? 'border-amber/40 bg-amber/10' : 'border-line'}`}
          >
            <input
              type="checkbox"
              className="mt-0.5 accent-amber"
              aria-label={`${label}: ${counts[kind].toLocaleString()} loaded records`}
              checked={options[kind]}
              onChange={(event) => updateOptions({ [kind]: event.target.checked })}
            />
            <span className="flex-1">
              <span className="block font-medium">{label}</span>
              <span className="mt-1 block text-[11px] text-muted">{note}</span>
            </span>
            <span className="font-mono text-muted">{counts[kind].toLocaleString()}</span>
          </label>
        ))}
      </fieldset>
      {!options.thermal && !options.wildfire && (
        <p className="text-xs text-muted">No fire evidence types selected.</p>
      )}
      <p className="text-[11px] leading-relaxed text-muted">
        Satellite detections are acquisition snapshots, not a live fire perimeter. Heat can also
        come from industry or volcanoes. Nearby detections may describe the same fire and are not
        extra independent reports.
      </p>
      <p className="text-[11px] leading-relaxed text-muted">
        Counts are loaded records, not unique fires. FIRMS may be geographically sampled. The shared
        nation, time and location-quality filters apply; natural-hazard refinements do not change
        fire records.
      </p>
    </section>
  );
}
