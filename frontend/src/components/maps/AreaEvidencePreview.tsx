import { useMemo, useState } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { LocalCollection } from '@/lib/map/geoJsonTypes';
import type { AreaResearchInterval } from '@/lib/areaResearchDraft';
import { previewAreaEvidence } from '@/lib/map/areaEvidencePreview';

interface Props {
  area: LocalCollection;
  events: readonly LiveEvent[];
  days: number;
  interval: AreaResearchInterval | null;
  onHighlight?: (event: LiveEvent) => void;
}
const stamp = (value: string) => new Date(value).toLocaleString('en-GB', { timeZone: 'UTC' });

export function AreaEvidencePreview({ area, events, days, interval, onHighlight }: Props) {
  const [openedAt] = useState(Date.now);
  const until = interval ? Date.parse(interval.until) : openedAt;
  const since = interval ? Date.parse(interval.since) : until - days * 86400000;
  const preview = useMemo(
    () => previewAreaEvidence(area, events, since, until),
    [area, events, since, until],
  );
  const categories = new Map<string, number>();
  for (const event of preview.inside)
    categories.set(event.category, (categories.get(event.category) ?? 0) + 1);
  return (
    <section aria-label="Retained evidence in this area" className="map-tool-section">
      <h3 className="map-tool-section-title">What is already loaded here?</h3>
      <p className="map-tool-result">
        {preview.inside.length} precisely located observations inside
      </p>
      <p className="map-tool-help">
        Checks {events.length} records currently loaded by this map, using publication time from{' '}
        {stamp(new Date(since).toISOString())} to {stamp(new Date(until).toISOString())} UTC (end
        excluded). Map filters and retention can limit this sample. No provider or AI is contacted.
      </p>
      <p className="map-tool-help">
        Research collectors may use acquisition time and collect additional evidence. This preview
        does not establish complete coverage or an absence of activity.
      </p>
      {categories.size > 0 && (
        <p className="map-tool-help">
          {[...categories].map(([name, count]) => `${name}: ${count}`).join(' · ')}
        </p>
      )}
      <ul className="map-tool-list">
        <li>
          Approximate markers inside: {preview.approximate.length}, not confirmed inside the
          boundary.
        </li>
        <li>Precisely located outside: {preview.outside}.</li>
        <li>
          Approximate markers outside: {preview.approximateOutside}, area membership uncertain.
        </li>
        <li>
          Country-level records: {preview.country}; unlocated: {preview.unlocated}. Area membership
          unknown.
        </li>
        <li>
          Outside the period: {preview.outOfPeriod}; no publication time: {preview.unknownTime}.
        </li>
      </ul>
      {[
        { label: 'Precisely inside', records: preview.inside },
        { label: 'Approximate context', records: preview.approximate },
      ].map(({ label, records }) => {
        return (
          records.length > 0 && (
            <details key={label} className="map-tool-disclosure">
              <summary>
                {label} ({records.length})
              </summary>
              <ul className="map-tool-list">
                {records.slice(0, 20).map((event) => (
                  <li key={event.id} className="py-2">
                    {onHighlight ? (
                      <button
                        type="button"
                        className="map-tool-text-button"
                        onClick={() => onHighlight(event)}
                      >
                        {event.title_en ?? event.title}
                      </button>
                    ) : (
                      <p>{event.title_en ?? event.title}</p>
                    )}
                    <p className="map-tool-help">
                      {event.source_id} · {stamp(event.published_at ?? '')} UTC ·{' '}
                      {event.geo_confidence}
                    </p>
                  </li>
                ))}
              </ul>
              {records.length > 20 && (
                <p className="map-tool-help">Showing the 20 newest records in this group.</p>
              )}
            </details>
          )
        );
      })}
    </section>
  );
}
