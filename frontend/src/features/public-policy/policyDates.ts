const format = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
});

/** A calendar date from the policy content, such as "18 October 2026", independent of time zone. */
export function formatPolicyDate(isoDate: string): string {
  return format.format(new Date(`${isoDate}T00:00:00Z`));
}
