import type { SatelliteGroup } from '@/lib/satellites';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { SatelliteResults } from './SatelliteResults';
import { SATELLITE_QUERY_LIMIT } from './satelliteSearch';

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
  query,
  setQuery,
  results,
  searching,
  onSelect,
  selectedId,
}: {
  group: SatelliteGroup;
  setGroup: (value: SatelliteGroup) => void;
  counts: Record<SatelliteGroup, number>;
  query: string;
  setQuery: (value: string) => void;
  results: LiveEvent[];
  searching: boolean;
  onSelect?: ((event: LiveEvent) => void) | undefined;
  selectedId?: string | null | undefined;
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
      <label className="block text-xs">
        Find a satellite
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          maxLength={SATELLITE_QUERY_LIMIT}
          placeholder="Name, NORAD number or designator"
          className="mt-2 min-h-11 w-full rounded border border-line bg-surface p-2"
        />
      </label>
      <p role="status" className="text-xs text-muted">
        {searching
          ? 'Updating satellite results…'
          : `${results.length.toLocaleString('en-GB')} matching satellites`}
      </p>
      <p className="text-[11px] text-muted">
        Search filters both the map and this list. Select a result to locate it.
      </p>
      <SatelliteResults
        key={`${group}:${query.trim().toLocaleLowerCase('en-GB')}`}
        results={results}
        onSelect={onSelect}
        selectedId={selectedId}
      />
      <p className="text-[11px] leading-relaxed text-muted">
        Positions are predicted from public orbital elements, not live observations. Element age is
        shown in details; older elements are labelled stale.
      </p>
      <p className="text-[11px] leading-relaxed text-muted">
        Catalogue counts reflect loaded objects before search. Military coverage is incomplete.
        Skynet includes historical spacecraft and does not imply current service.
      </p>
    </section>
  );
}
