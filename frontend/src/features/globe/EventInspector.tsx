import { SourceProvenanceDetails } from '@/components/reports/SourceProvenanceDetails';
import { Fragment, useEffect, useRef } from 'react';
import { Link } from 'react-router';

import { isMappedEvent, precisionLabel } from './geographicPrecision';
import { eventResearchHref } from '@/lib/researchNavigation';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { formatUtc } from '@/lib/format';
import { isHttpUrl } from '@/lib/urls';

import { CATEGORY_STYLES } from '@/lib/categories';

export interface EventInspectorProps {
  event: LiveEvent;
  /** How many live items share this event's story, including itself. */
  storySize?: number;
  onClose: () => void;
}

export { isHttpUrl };

export function sourceLabel(sourceId: string): string {
  return sourceId.replace(/_/g, ' ');
}

const dl =
  'grid grid-cols-[minmax(0,auto)_minmax(0,1fr)] gap-x-3 gap-y-1 break-words font-mono text-xs';

/** The detail drawer for the selected event: grade, provenance, summary and attributes. */
export function EventInspector({ event, storySize = 1, onClose }: EventInspectorProps) {
  const closeButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const opener = document.activeElement;
    closeButton.current?.focus();
    return () => {
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, []);
  useEffect(() => {
    const onKeyDown = (key: KeyboardEvent) => {
      if (key.key !== 'Escape' || key.defaultPrevented) return;
      if (
        key.target instanceof Element &&
        key.target.closest('dialog[open], input, textarea, select')
      )
        return;
      key.preventDefault();
      onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose]);
  const style = CATEGORY_STYLES[event.category];
  const attributes = Object.entries(event.attributes).filter(
    ([, value]) => value !== null && value !== '',
  );
  return (
    <aside
      aria-label="Event details"
      // Stops above the map attribution, which must stay visible (OpenFreeMap licence).
      className="absolute top-32 right-3 bottom-40 z-10 flex w-[calc(100%-1.5rem)] flex-col rounded-md border border-line bg-surface/95 backdrop-blur sm:w-80 lg:top-16 lg:bottom-40"
    >
      <div className="flex items-start justify-between gap-2 border-b border-line p-3">
        <div className="flex flex-wrap items-center gap-1.5">
          <span
            className="inline-flex items-center gap-1.5 rounded px-1.5 py-0.5 font-mono text-[11px] uppercase tracking-wider"
            style={{ color: style.css, backgroundColor: `${style.css}1f` }}
          >
            <span
              aria-hidden="true"
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: style.css }}
            />
            {style.label}
          </span>
          <span
            className="rounded border border-line px-1.5 py-0.5 font-mono text-[11px] text-text"
            title={event.grade_rationale}
          >
            Grade {event.grade}
          </span>
          <span className="font-mono text-[11px] uppercase tracking-wider text-muted">
            {event.subtype}
          </span>
        </div>
        <button
          ref={closeButton}
          type="button"
          aria-label="Close"
          onClick={onClose}
          className="min-h-11 min-w-11 rounded-md px-2 py-1 text-muted hover:bg-surface-2 hover:text-text focus-visible:outline-2 focus-visible:outline-ember lg:min-h-0 lg:min-w-0"
        >
          ×
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto break-words p-3 text-sm">
        <h2 className="text-base leading-snug font-semibold text-text">{event.title}</h2>
        {event.title_en !== null && event.title_en !== event.title && (
          <p className="mt-1 text-muted">{event.title_en}</p>
        )}
        {event.grade_rationale !== '' && (
          <p className="mt-2 text-xs text-muted">
            <span className="font-mono text-text">{event.grade}</span> {event.grade_rationale}
            {storySize > 1 ? ` (story of ${storySize} items)` : ''}
          </p>
        )}
        <dl className={`mt-3 text-muted ${dl}`}>
          <dt>Source</dt>
          <dd className="text-text">{sourceLabel(event.source_id)}</dd>
          <dt>{event.subtype === 'vessel_position' ? 'Position record time' : 'Published'}</dt>
          <dd className="text-text">{formatUtc(event.published_at)}</dd>
          <dt>Location precision</dt>
          <dd className="text-text">{precisionLabel(event)}</dd>
          {event.point !== null && isMappedEvent(event) && (
            <>
              <dt>{event.geo_confidence === 'exact' ? 'Position' : 'Reference position'}</dt>
              <dd className="text-text">
                {event.point.lat.toFixed(3)}, {event.point.lon.toFixed(3)} ({event.geo_confidence})
              </dd>
            </>
          )}
          {event.country_iso !== null && (
            <>
              <dt>Country</dt>
              <dd className="text-text">{event.country_iso}</dd>
            </>
          )}
          {event.severity !== null && (
            <>
              <dt>Severity</dt>
              <dd className="text-text">{Math.round(event.severity * 100)}%</dd>
            </>
          )}
        </dl>
        {event.summary !== null && (
          <p className="mt-3 whitespace-pre-line text-text">{event.summary}</p>
        )}
        <SourceProvenanceDetails
          transformations={event.transformations}
          dates={event.source_dates}
        />
        {attributes.length > 0 && (
          <dl className={`mt-3 ${dl}`}>
            {attributes.map(([key, value]) => (
              <Fragment key={key}>
                <dt className="text-muted">{key}</dt>
                <dd className="break-words text-text">{String(value)}</dd>
              </Fragment>
            ))}
          </dl>
        )}
        {event.tags.length > 0 && (
          <p className="mt-3 flex flex-wrap gap-1">
            {event.tags.map((tag) => (
              <span
                key={tag}
                className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-muted"
              >
                {tag}
              </span>
            ))}
          </p>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-x-4 border-t border-line px-3 py-1">
        <Link
          to={eventResearchHref(event)}
          className="inline-flex min-h-11 items-center text-sm text-ember hover:underline focus-visible:outline-2 focus-visible:outline-ember"
          title="Review the question before starting research"
        >
          Research this
        </Link>
        {isHttpUrl(event.url) && (
          <a
            href={event.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex min-h-11 items-center text-sm text-muted hover:underline"
          >
            Open source
          </a>
        )}
      </div>
    </aside>
  );
}
