import { useMemo, useState } from 'react';
import { Link } from 'react-router';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { describeError } from '@/lib/api/errors';
import { SourceLink } from '@/components/ui/SourceLink';
import { MapToolIntro } from '@/components/maps/MapToolIntro';
import { formatUtc } from '@/lib/format';
import { isMappedEvent, precisionLabel } from './geographicPrecision';
import {
  DEFAULT_NEWS_OPTIONS,
  NEWS_SUBJECTS,
  matchesNews,
  newsStories,
  newsSourceLabel,
} from './newsFilters';
import type { useNewsFilters } from './newsFilters';
import { useMapNewsFeed } from './useMapNewsFeed';

export function NewsPanel({
  filters,
  country,
  windowHours,
  mapStatus,
  onSelect,
}: {
  filters: ReturnType<typeof useNewsFilters>;
  country: string | null;
  windowHours: number | null;
  mapStatus?: { loading: boolean; error: unknown; mapped: number; countries: number };
  onSelect: (event: LiveEvent) => void;
}) {
  const snapshot = useMapNewsFeed(country, windowHours);
  const { options, setOptions } = filters;
  const stories = useMemo(
    () => newsStories((snapshot.data?.items ?? []).filter((event) => matchesNews(event, options))),
    [snapshot.data, options],
  );
  const sources = useMemo(
    () =>
      [
        ...new Map(
          snapshot.data?.items.map((event) => [event.source_id, newsSourceLabel(event)]),
        ).entries(),
      ].sort((a, b) => a[1].localeCompare(b[1])),
    [snapshot.data],
  );
  const [limit, setLimit] = useState(15);
  const change = (next: Partial<typeof options>) => {
    setOptions((current) => ({ ...current, ...next }));
    setLimit(15);
  };
  return (
    <section className="map-tool-workspace" aria-label="News briefing">
      <MapToolIntro
        title="News briefing"
        description="Source-linked headlines, evidence and map locations."
      />
      {filters.enabled && mapStatus && (
        <p role={mapStatus.error ? 'alert' : 'status'} className="map-tool-notice">
          {mapStatus.error
            ? describeError(mapStatus.error)
            : mapStatus.loading
              ? 'Loading news map locations…'
              : `${mapStatus.mapped} located reports · ${mapStatus.countries} country references on the map.`}{' '}
          The map uses a geographic sample, refreshed every minute. GDELT recency uses indexing
          time, not publication. This list shows recent headlines.
        </p>
      )}
      <p className="map-tool-help">
        {country ? `Nation: ${country}` : 'Worldwide'} ·{' '}
        {windowHours === null ? 'Retained period' : `Last ${windowHours} hours`}
      </p>
      <label className="map-tool-field">
        Search headlines
        <input
          type="search"
          className="map-tool-input"
          maxLength={120}
          value={options.query}
          placeholder="Topic, place or keyword"
          onChange={(event) => change({ query: event.target.value })}
        />
      </label>
      <label className="map-tool-field">
        Publisher
        <select
          className="map-tool-input"
          value={options.source}
          onChange={(event) => change({ source: event.target.value })}
        >
          <option value="">All publishers in this snapshot</option>
          {sources.map(([source, label]) => (
            <option key={source} value={source}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <details className="map-tool-disclosure">
        <summary className="min-h-9 cursor-pointer py-2">News subjects</summary>
        <fieldset className="space-y-1">
          <legend className="sr-only">Include reporting subjects</legend>
          {NEWS_SUBJECTS.map((subject) => (
            <label key={subject.id} className="flex min-h-10 items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={options.categories.includes(subject.id)}
                onChange={() =>
                  change({
                    categories: options.categories.includes(subject.id)
                      ? options.categories.filter((id) => id !== subject.id)
                      : [...options.categories, subject.id],
                  })
                }
              />
              {subject.label}
            </label>
          ))}
        </fieldset>
        <p className="map-tool-help">
          These choices filter this list and the News map layer. Reading headlines does not switch
          map layers on.
        </p>
      </details>
      <div className="flex items-center justify-between gap-3 border-t border-line pt-2">
        <button
          className="map-tool-text-button"
          type="button"
          onClick={() => {
            setOptions(DEFAULT_NEWS_OPTIONS);
            setLimit(15);
          }}
        >
          Clear news filters
        </button>
        <button
          className="map-tool-text-button"
          type="button"
          disabled={snapshot.loading}
          onClick={() => void snapshot.reload()}
        >
          Refresh headlines
        </button>
      </div>
      {!filters.enabled && (
        <p className="text-[11px] text-muted">News map layer is off. Headlines remain readable.</p>
      )}
      {snapshot.loading && (
        <p role="status" className="map-tool-help">
          Loading retained news…
        </p>
      )}
      {snapshot.error && (
        <p role="alert" className="map-tool-notice">
          {describeError(snapshot.error)}
        </p>
      )}
      {snapshot.data && (
        <>
          <p className="map-tool-help">
            {stories.length} matching {stories.length === 1 ? 'story' : 'stories'} from{' '}
            {
              new Set(stories.flatMap((story) => story.records.map((event) => event.source_id)))
                .size
            }{' '}
            source feeds.
          </p>
          {!stories.length && (
            <p className="map-tool-help">
              No headlines match this snapshot. Broaden the time window, clear the nation or adjust
              your search.
            </p>
          )}
          <ol className="divide-y divide-line" aria-label="News stories">
            {stories.slice(0, limit).map(({ lead, records }) => (
              <li key={lead.id} className="space-y-3 py-4">
                <p className="font-mono text-[10px] text-muted">
                  {newsSourceLabel(lead)} ·{' '}
                  {lead.published_at ? formatUtc(lead.published_at) : 'Publication date unknown'}
                </p>
                <h3 className="text-sm font-semibold leading-6">{lead.title_en ?? lead.title}</h3>
                <SourceLink url={lead.url}>Read source</SourceLink>
                {lead.summary && lead.summary !== lead.title && (
                  <p className="line-clamp-3 text-xs leading-6 text-muted">{lead.summary}</p>
                )}
                <p className="text-[10px] text-muted">
                  {precisionLabel(lead)}
                  {records.length > 1 ? ` · ${records.length} related reports` : ''}
                </p>
                {lead.source_id === 'gdelt_news' && (
                  <p className="text-[10px] leading-5 text-muted">
                    GDELT-coded action geography, not a verified event position. Map recency uses
                    GDELT indexing time; publisher publication time is unknown.
                  </p>
                )}
                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    className="map-tool-text-button"
                    onClick={() => onSelect(lead)}
                  >
                    {isMappedEvent(lead) ? 'Locate and inspect' : 'Inspect evidence'}
                  </button>
                  <Link
                    className="map-tool-text-button"
                    to={`/research?${new URLSearchParams({ question: `Assess the evidence behind this reporting: ${lead.title}. Check original sources, corroboration, contradictory reporting and uncertainty.` })}`}
                  >
                    Research story
                  </Link>
                </div>
                <details className="text-xs leading-5 text-muted">
                  <summary className="cursor-pointer">Source assessment · {lead.grade}</summary>
                  <p className="mt-2">
                    Reliability {lead.reliability}; information credibility {lead.credibility}.{' '}
                    {lead.grade_rationale}
                  </p>
                  <p className="mt-2">
                    F or 6 means unassessed, not false. Grades assess evidence; they are not a
                    percentage probability that this story is true.
                  </p>
                  {records.length > 1 && (
                    <ul className="mt-2 space-y-2">
                      {records.slice(0, 8).map((item) => (
                        <li key={item.id}>
                          {newsSourceLabel(item)}: {item.title}{' '}
                          <SourceLink url={item.url}>Read source</SourceLink>
                        </li>
                      ))}
                    </ul>
                  )}
                </details>
              </li>
            ))}
          </ol>
          {stories.length > limit && (
            <button
              type="button"
              className="map-tool-text-button"
              onClick={() => setLimit((value) => value + 15)}
            >
              Show more headlines
            </button>
          )}
          <details className="map-tool-disclosure">
            <summary className="cursor-pointer py-2 text-xs">
              Coverage and source independence
            </summary>
            <p className="map-tool-help">
              Use Event time to change the shared period. A nation filter requires source-supported
              location, not publisher nationality. Related reports are grouped, not counted as
              independent confirmation.
            </p>
            <p className="map-tool-help">
              Snapshot {formatUtc(snapshot.data.fetchedAt)}. Up to 300 retained records; this is not
              the full publisher archive.{' '}
              {snapshot.data.items.length >= 300 ? 'The snapshot reached its limit. ' : ''}Headlines
              without a reliable position are readable here and are not given invented map
              locations.
            </p>
          </details>
        </>
      )}
    </section>
  );
}
