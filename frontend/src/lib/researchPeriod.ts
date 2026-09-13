/** Shared UTC period validation for reviewable research drafts and form submission. */
export const MAX_RESEARCH_HOURS = 730 * 24;
export interface ResearchDates {
  since: string;
  until: string;
}

export function researchDateError(dates: ResearchDates, now = Date.now()): string | null {
  const start = Date.parse(dates.since);
  const end = Date.parse(dates.until);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start)
    return 'Choose a start and end date, with the end after the start.';
  if (end - start > MAX_RESEARCH_HOURS * 3_600_000)
    return 'Choose a search period of no more than two years (730 days).';
  if (end > now) return 'The end of the search period cannot be in the future.';
  return null;
}
