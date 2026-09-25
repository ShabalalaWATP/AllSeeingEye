/** Reviewable research drafts from public context; navigation never starts collection. */
import type { LiveEvent } from './api/eventSchemas';
import { researchDateError, type ResearchDates } from './researchPeriod';

export function researchHref(
  question: string,
  country?: string | null,
  timeRange?: ResearchDates | null,
): string {
  const params = new URLSearchParams({ question: question.trim().slice(0, 1000) });
  const iso = country?.trim().toUpperCase();
  if (iso && /^[A-Z]{2}$/.test(iso)) params.set('country', iso);
  if (timeRange && !researchDateError(timeRange)) {
    params.set('since', timeRange.since);
    params.set('until', timeRange.until);
  }
  return `/research?${params.toString()}`;
}

/** Treat navigation parameters as hints only; the research form validates again on submit. */
export function readResearchDraftDates(params: URLSearchParams): ResearchDates | null {
  const since = params.get('since');
  const until = params.get('until');
  if (!since || !until || since.length > 40 || until.length > 40) return null;
  const dates = { since, until };
  return researchDateError(dates) ? null : dates;
}

/** A subscription is a reviewable draft; navigation cannot create or start it. */
export function subscriptionHref(question: string, country?: string | null): string {
  const params = new URLSearchParams({ question: question.trim().slice(0, 1000) });
  const iso = country?.trim().toUpperCase();
  if (iso && /^[A-Z]{2}$/.test(iso)) params.set('country', iso);
  return `/subscriptions?${params.toString()}`;
}

const HOUR = 3_600_000;
/** Either side of the event, so the draft reads what came before it as well as after. */
export const EVENT_CONTEXT_HOURS = 72;
/** Country centroids and unplaced events have no meaningful position to pass on. */
const PRECISION: Partial<Record<LiveEvent['geo_confidence'], string>> = {
  exact: 'exact position',
  city: 'city-level position',
  admin1: 'regional position',
};

const minute = (ms: number) => new Date(Math.floor(ms / 60_000) * 60_000).toISOString();
const eventTime = (event: LiveEvent) => Date.parse(event.published_at ?? event.observed_at);

/** A research period around the event, never reaching past now; null when the time is unusable. */
export function eventResearchPeriod(event: LiveEvent, now = Date.now()): ResearchDates | null {
  const at = eventTime(event);
  if (!Number.isFinite(at)) return null;
  const dates = {
    since: minute(at - EVENT_CONTEXT_HOURS * HOUR),
    until: minute(Math.min(at + EVENT_CONTEXT_HOURS * HOUR, now)),
  };
  return researchDateError(dates, now) ? null : dates;
}

function eventContext(event: LiveEvent): string {
  const at = eventTime(event);
  const details: string[] = [];
  if (Number.isFinite(at))
    details.push(`reported at ${new Date(at).toISOString().slice(0, 16).replace('T', ' ')} UTC`);
  const precision = PRECISION[event.geo_confidence];
  const { point } = event;
  if (precision && point && Math.abs(point.lat) <= 90 && Math.abs(point.lon) <= 180)
    details.push(
      `mapped near latitude ${point.lat.toFixed(2)}, longitude ${point.lon.toFixed(2)} (${precision})`,
    );
  return details.length ? ` It was ${details.join(' and ')}.` : '';
}

/**
 * The event's title, time and mapped position go into the question, its country into the
 * scope and a period around it into the dates. The research form reviews all of it again.
 */
export function eventResearchHref(event: LiveEvent, now = Date.now()): string {
  const title = event.title.replace(/\s+/g, ' ').trim().slice(0, 650);
  return researchHref(
    `What public evidence supports or challenges the report titled "${title}"?${eventContext(event)} Check its timing, location and source provenance, and distinguish claims from established facts.`,
    event.country_iso,
    eventResearchPeriod(event, now),
  );
}
