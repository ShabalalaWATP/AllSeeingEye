import { useCallback } from 'react';
import { Link, useParams } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { describeError } from '@/lib/api/errors';
import { fetchDisasterDetail } from '@/lib/api/trackers';
import { useResource } from '@/lib/hooks/useResource';

import { ActivityCells, BackToTrackers, EventRow, ShowOnGlobe, Timeline } from './TrackerParts';

export default function HazardPage() {
  const { hazard = '' } = useParams();
  const loader = useCallback(() => fetchDisasterDetail(hazard), [hazard]);
  const { data, error, loading } = useResource(loader);
  if (data === null) {
    return (
      <section className="p-6">
        {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
        {loading ? <LoadingNote label="Loading hazard" /> : null}
      </section>
    );
  }
  const { card, timeline, events } = data;
  return (
    <article className="flex h-full flex-col gap-5 overflow-y-auto p-6">
      <header className="flex flex-col gap-2">
        <BackToTrackers />
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold">{card.title}</h1>
          {card.red_alerts > 0 && (
            <span className="rounded bg-critical/15 px-1.5 py-0.5 font-mono text-[11px] text-critical">
              {card.red_alerts} red alerts / 7 d
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <ActivityCells activity={card.activity} />
          {card.countries.length > 0 && (
            <span className="font-mono text-xs text-muted">{card.countries.join(' ')}</span>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <ShowOnGlobe country={card.countries[0] ?? null} />
          <Link
            to={`/reports?template=disaster_sitrep&hazard=${card.hazard}`}
            className="rounded-md border border-line bg-surface-2 px-3 py-2 text-sm text-text hover:bg-surface"
          >
            Generate SITREP
          </Link>
        </div>
      </header>
      <section aria-label="Events by day" className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">Fourteen days</h2>
        <Timeline buckets={timeline} label="Events by day" />
      </section>
      {card.top !== null && (
        <section aria-label="Most severe this week" className="flex flex-col gap-1">
          <h2 className="text-base font-semibold">Most severe this week</h2>
          <ul>
            <EventRow event={card.top} />
          </ul>
        </section>
      )}
      <section aria-label="Latest events" className="flex flex-col gap-1">
        <h2 className="text-base font-semibold">Latest</h2>
        {events.length === 0 ? (
          <p className="text-sm text-muted">Nothing in the retained window.</p>
        ) : (
          <ul>
            {events.map((event) => (
              <EventRow key={event.id} event={event} />
            ))}
          </ul>
        )}
      </section>
    </article>
  );
}
