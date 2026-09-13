import { BarList } from '@/components/charts/BarList';
import type { CyberActor, CyberSnapshot } from '@/lib/api/cyber';
import { ChartCard } from './CyberCharts';
import { mentionedActors, stateRows } from './cyberModel';

/** Which reference-associated states appear in this period's name matches, and through whom. */
export function CyberNationState({
  data,
  actors,
  actorStatus,
  onActor,
}: {
  data: CyberSnapshot;
  actors: readonly CyberActor[];
  actorStatus: 'ready' | 'loading' | 'unavailable';
  onActor: (id: string) => void;
}) {
  const states = stateRows(data, actors);
  const mentioned = mentionedActors(data, actors);
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ChartCard title="States named in mentioned actors' profiles" note="Records per state">
        <BarList
          rows={states.map((row) => ({
            ...row,
            note: row.actors.slice(0, 3).join(', ') || undefined,
          }))}
          label="Records mentioning actors with a recorded state association"
          slot={5}
          emptyText={
            actorStatus === 'unavailable'
              ? 'The actor reference is unavailable, so no state associations can be shown.'
              : 'No returned record names a group whose reference profile records a state association.'
          }
        />
        <p className="mt-3 text-xs leading-5 text-muted">
          A state is listed when the MITRE ATT&CK profile of a mentioned group itself states an
          association (for example “attributed to” or “state-sponsored”). A record counts once per
          state. This is the profile’s wording, not this application’s attribution of any new
          incident.
        </p>
      </ChartCard>
      <ChartCard title="Actor names in reporting" note="Matched mentions">
        {mentioned.length ? (
          <ul className="divide-y divide-line/60">
            {mentioned.map((actor) => (
              <li key={actor.group_id}>
                <button
                  type="button"
                  onClick={() => onActor(actor.group_id)}
                  className="flex min-h-11 w-full items-center justify-between gap-3 rounded-md px-2 text-left text-sm hover:bg-surface-2"
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{actor.name}</span>
                    <span className="block text-[11px] text-muted">
                      {actor.state
                        ? `Profile association: ${actor.state}`
                        : 'No state association in the profile'}
                    </span>
                  </span>
                  <span className="shrink-0 font-mono text-xs text-muted tabular-nums">
                    {actor.count} {actor.count === 1 ? 'record' : 'records'}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs leading-5 text-muted">
            {actorStatus === 'loading'
              ? 'Loading the actor reference…'
              : 'No distinctive actor names matched the returned reporting.'}
          </p>
        )}
        <p className="mt-3 text-xs leading-5 text-muted">
          Matched mentions, not a ranking of capability. Select a name to open its reference profile
          below.
        </p>
      </ChartCard>
    </div>
  );
}
