/** Validate explicit specialist identifiers before an unsupported collection is started. */
export function recordScopeError(subject: string, country: string): string | null {
  if (subject.startsWith('academic:') && country)
    return 'Choose All countries for scholarly publication research.';
  if (subject.startsWith('parliament:') && country && country !== 'GB')
    return 'Choose United Kingdom or All countries for parliamentary research.';
  if (subject.startsWith('WB:')) {
    const match = /^WB:([A-Za-z]{2}):([A-Z][A-Z0-9_.]{1,79}):(\d{4}):(\d{4})$/.exec(subject);
    const start = Number(match?.[3]),
      end = Number(match?.[4]);
    if (!match || start < 1900 || end > 2100 || end < start || end - start >= 20) {
      return 'Choose a country, indicator and a valid range of up to 20 years between 1900 and 2100.';
    }
    if (country && country !== match[1]?.toUpperCase())
      return 'Match the country filter to the World Bank record country, or choose All countries.';
  }
  if (subject.startsWith('ooni:')) {
    const target = subject.slice(5).toUpperCase();
    if (!/^[A-Z]{2}$/.test(target)) return 'Choose a two-letter country for OONI measurements.';
    if (country && country !== target)
      return 'Match the country filter to the OONI record country, or choose All countries.';
  }
  return null;
}
