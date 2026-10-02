import { describe, expect, it } from 'vitest';
import { report } from '@/test/fixtures';
import { followUpAvailability, followUpRequest } from './followUpScope';

function parent(regions: unknown, countries: string[] = []) {
  return {
    ...report,
    report: {
      ...report.report,
      scope: { research_mode: 'quick', research_focus: 'general', regions, countries },
    },
  };
}

describe('regional follow-up scope', () => {
  it.each([{ countries: [] }, { countries: ['US'] }])(
    'retains saved regions alongside $countries',
    ({ countries }) => {
      const request = followUpRequest(parent(['europe', 'middle_east'], countries));
      expect(request.regions).toEqual(['europe', 'middle_east']);
      expect(request.countries).toEqual(countries);
    },
  );

  it('normalises repeated region choices without losing the restriction', () => {
    expect(followUpRequest(parent(['europe', 'europe'])).regions).toEqual(['europe']);
  });

  it.each([null, 'europe', ['unknown']])('refuses malformed saved regions %j', (regions) => {
    expect(followUpAvailability(parent(regions)).request).toBeNull();
  });

  it('keeps legacy country-only follow-ups valid', () => {
    const request = followUpRequest({
      ...report,
      report: { ...report.report, scope: { countries: ['GB'], research_mode: 'quick' } },
    });
    expect(request.countries).toEqual(['GB']);
    expect(request.regions).toEqual([]);
  });
});
