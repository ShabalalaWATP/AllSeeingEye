import { describeError } from '@/lib/api/errors';
import { formatUtc } from '@/lib/format';
import { fetchMaritimeBoard, fetchSpaceBoard } from '@/lib/api/modules';
import { useResource } from '@/lib/hooks/useResource';

import { EventList, ModulePage, Stat, TallyChips } from './ModuleParts';

export function MaritimePage() {
  const { data, error, loading } = useResource(fetchMaritimeBoard);
  return (
    <ModulePage
      title="Maritime"
      blurb="Broadcast warnings at sea: exercises and closures, security incidents, GNSS interference notices and navigational hazards, from the NAVAREA coordinators."
      template="maritime_activity"
      loading={loading}
      error={error === null ? null : describeError(error)}
    >
      {data !== null && (
        <>
          <div className="grid gap-2 sm:grid-cols-2">
            <Stat label="Active warnings" value={data.warnings_total} />
            <Stat label="With positions" value={data.located} />
          </div>
          <section aria-label="By area" className="flex flex-col gap-2">
            <h2 className="text-base font-semibold">By NAVAREA</h2>
            <TallyChips label="Warnings by area" rows={data.by_area} />
          </section>
          <section aria-label="By kind" className="flex flex-col gap-2">
            <h2 className="text-base font-semibold">By kind</h2>
            <TallyChips label="Warnings by kind" rows={data.by_kind} />
          </section>
          <EventList label="Notable warnings" events={data.notable} />
          <EventList label="Latest warnings" events={data.latest} />
        </>
      )}
    </ModulePage>
  );
}

export function SpacePage() {
  const { data, error, loading } = useResource(fetchSpaceBoard);
  return (
    <ModulePage
      title="Space"
      blurb="Crewed stations propagated from published orbital elements, the launch schedule, and the geomagnetic picture from the Space Weather Prediction Center."
      template={null}
      loading={loading}
      error={error === null ? null : describeError(error)}
    >
      {data !== null && (
        <>
          <div className="grid gap-2 sm:grid-cols-3">
            <Stat
              label="Planetary K index"
              value={
                data.kp === null ? 'no data' : `${data.kp.toFixed(2)} ${data.kp_level ?? ''}`.trim()
              }
            />
            <Stat label="Space weather alerts, 24 h" value={data.alerts_24h} />
            <Stat label="Upcoming launches" value={data.launches.length} />
          </div>
          <section aria-label="Stations" className="flex flex-col gap-1">
            <h2 className="text-base font-semibold">Stations now</h2>
            <ul className="flex flex-col gap-1 text-sm">
              {data.stations.map((station) => (
                <li key={station.id} className="flex flex-wrap items-baseline gap-2">
                  <span className="font-medium">{station.title}</span>
                  <span className="font-mono text-xs text-muted">
                    {station.point === null
                      ? 'position unknown'
                      : `${station.point.lat.toFixed(1)}, ${station.point.lon.toFixed(1)}`}
                    {typeof station.attributes.altitude_km === 'number'
                      ? ` · ${String(Math.round(station.attributes.altitude_km))} km`
                      : ''}
                  </span>
                </li>
              ))}
            </ul>
          </section>
          <section aria-label="Launches" className="flex flex-col gap-1">
            <h2 className="text-base font-semibold">Launches</h2>
            <ul className="flex flex-col gap-1 text-sm">
              {data.launches.map((launch) => (
                <li key={launch.id} className="flex flex-wrap items-baseline gap-2">
                  <span className="font-mono text-xs text-muted">
                    {typeof launch.attributes.net === 'string'
                      ? formatUtc(launch.attributes.net)
                      : ''}
                  </span>
                  <span>{launch.title}</span>
                </li>
              ))}
            </ul>
          </section>
          <EventList label="Space weather alerts" events={data.latest_alerts} />
        </>
      )}
    </ModulePage>
  );
}
