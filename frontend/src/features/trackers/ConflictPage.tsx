import { useCallback } from 'react';
import { useParams } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { describeError } from '@/lib/api/errors';
import { fetchConflictDetail } from '@/lib/api/trackers';
import { useResource } from '@/lib/hooks/useResource';

import { ActivityCells, BackToTrackers, EventRow, ShowOnGlobe, Timeline } from './TrackerParts';

export default function ConflictPage() {
  const { id = '' } = useParams();
  const loader = useCallback(() => fetchConflictDetail(id), [id]);
  const { data, error, loading } = useResource(loader);
  if (data === null) {
    return (
      <section className="p-6">
        {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
        {loading ? <LoadingNote label="Loading conflict" /> : null}
      </section>
    );
  }
  const { card, timeline, events } = data;
  const { conflict } = card;
  return (
    <article className="flex h-full flex-col gap-5 overflow-y-auto p-6">
      <header className="flex flex-col gap-2">
        <BackToTrackers />
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold">{conflict.name}</h1>
          <span className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] uppercase text-muted">
            {conflict.status}
          </span>
        </div>
        <p className="text-sm text-muted">{conflict.summary}</p>
        <p className="font-mono text-xs text-muted">
          {conflict.countries.join(', ')} · {conflict.belligerents.join(' v ')}
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <ActivityCells activity={card.activity} />
          <span className="font-mono text-xs text-muted">
            {card.reporting_7d} related items / 7 d
          </span>
          {card.fatalities_7d > 0 && (
            <span className="font-mono text-xs text-critical">
              {card.fatalities_7d} reported deaths / 7 d
            </span>
          )}
        </div>
        <div>
          <ShowOnGlobe country={conflict.countries[0] ?? null} />
        </div>
      </header>
      <section aria-label="Conflict events by day" className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">Fourteen days</h2>
        <Timeline buckets={timeline} label="Conflict events by day" />
      </section>
      {card.top !== null && (
        <section aria-label="Most severe this week" className="flex flex-col gap-1">
          <h2 className="text-base font-semibold">Most severe this week</h2>
          <ul>
            <EventRow event={card.top} />
          </ul>
        </section>
      )}
      <section aria-label="Latest in the area" className="flex flex-col gap-1">
        <h2 className="text-base font-semibold">Latest in the area</h2>
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
