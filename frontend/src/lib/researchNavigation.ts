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

export function eventResearchHref(event: LiveEvent): string {
  const title = event.title.replace(/\s+/g, ' ').trim().slice(0, 650);
  return researchHref(
    `What public evidence supports or challenges the report titled "${title}"? Check its timing, location and source provenance, and distinguish claims from established facts.`,
    event.country_iso,
  );
}
