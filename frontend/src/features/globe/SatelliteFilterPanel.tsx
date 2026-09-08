import type { SatelliteGroup } from '@/lib/satellites';

const choices: { value: SatelliteGroup; label: string }[] = [
  { value: 'all', label: 'All satellites' },
  { value: 'crewed', label: 'Stations and crewed vehicles' },
  { value: 'military', label: 'Public military catalogue' },
  { value: 'skynet', label: 'Skynet' },
];

export function SatelliteFilterPanel({
  group,
  setGroup,
  counts,
}: {
  group: SatelliteGroup;
  setGroup: (value: SatelliteGroup) => void;
  counts: Record<SatelliteGroup, number>;
}) {
  return (
    <section aria-label="Satellite filters" className="space-y-3 p-3">
      <p className="text-xs text-muted">Choose the public orbital catalogue shown on the map.</p>
      <div className="space-y-1" role="radiogroup" aria-label="Satellite catalogue">
        {choices.map((choice) => (
          <button
            key={choice.value}
            type="button"
            role="radio"
            aria-checked={group === choice.value}
            onClick={() => setGroup(choice.value)}
            className={`flex w-full items-center justify-between gap-3 rounded-lg border px-3 py-2 text-left text-xs ${
              group === choice.value
                ? 'border-cyan-400/40 bg-cyan-400/10 text-cyan-200'
                : 'border-white/10 text-muted hover:bg-white/5'
            }`}
          >
            <span>{choice.label}</span>
            <span className="font-mono tabular-nums">{counts[choice.value].toLocaleString()}</span>
          </button>
        ))}
      </div>
      <p className="text-[11px] leading-relaxed text-muted">
        Positions are predicted from public orbital elements, not live observations. Element age is
        shown in details; older elements are labelled stale.
      </p>
      <p className="text-[11px] leading-relaxed text-muted">
        Counts reflect loaded objects. Military coverage is incomplete. Skynet includes historical
        spacecraft and does not imply current service.
      </p>
    </section>
  );
}
