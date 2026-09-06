/** Reviewable research drafts from public context; navigation never starts collection. */
import type { LiveEvent } from './api/eventSchemas';

export function researchHref(question: string, country?: string | null): string {
  const params = new URLSearchParams({ question: question.trim().slice(0, 1000) });
  const iso = country?.trim().toUpperCase();
  if (iso && /^[A-Z]{2}$/.test(iso)) params.set('country', iso);
  return `/research?${params.toString()}`;
}

export function eventResearchHref(event: LiveEvent): string {
  const title = event.title.replace(/\s+/g, ' ').trim().slice(0, 650);
  return researchHref(
    `What public evidence supports or challenges the report titled "${title}"? Check its timing, location and source provenance, and distinguish claims from established facts.`,
    event.country_iso,
  );
}
