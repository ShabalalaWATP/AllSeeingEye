/** Validate explicit specialist identifiers before an unsupported collection is started. */
export function recordScopeError(
  subject: string,
  selectedCountries: string | string[],
): string | null {
  const countries =
    typeof selectedCountries === 'string'
      ? selectedCountries
        ? [selectedCountries]
        : []
      : selectedCountries;
  const hasCountries = countries.length > 0;
  if (subject.startsWith('academic:') && hasCountries)
    return 'Choose worldwide for scholarly publication research.';
  if (subject.startsWith('parliament:') && hasCountries && !countries.includes('GB'))
    return 'Choose a scope including United Kingdom or worldwide for parliamentary research.';
  if (subject.startsWith('WB:')) {
    const match = /^WB:([A-Za-z]{2}):([A-Z][A-Z0-9_.]{1,79}):(\d{4}):(\d{4})$/.exec(subject);
    const start = Number(match?.[3]),
      end = Number(match?.[4]);
    if (!match || start < 1900 || end > 2100 || end < start || end - start >= 20) {
      return 'Choose a country, indicator and a valid range of up to 20 years between 1900 and 2100.';
    }
    if (hasCountries && !countries.includes(match[1]?.toUpperCase() ?? ''))
      return 'Include the World Bank record country in your countries, or choose worldwide.';
  }
  if (subject.startsWith('ooni:')) {
    const target = subject.slice(5).toUpperCase();
    if (!/^[A-Z]{2}$/.test(target)) return 'Choose a two-letter country for OONI measurements.';
    if (hasCountries && !countries.includes(target))
      return 'Include the OONI record country in your countries, or choose worldwide.';
  }
  return null;
}
