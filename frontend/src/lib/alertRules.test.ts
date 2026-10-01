import { describe, expect, it } from 'vitest';

import { indicator } from '@/test/fixtures';

import {
  COOLDOWN_RANGE,
  emptyRuleFields,
  ruleFieldsFromIndicator,
  ruleProblems,
  ruleRequest,
  ruleSummary,
  splitKeywords,
} from './alertRules';
import openapi from './api/openapi.json';

const known = new Set(['UA', 'GB', 'BY']);
const valid = {
  ...emptyRuleFields(),
  name: 'Sumy strikes',
  countries: ['UA'],
};

describe('alert rule fields', () => {
  it('uses the server cooldown range', () => {
    const schema = openapi.components.schemas.IndicatorIn.properties.cooldown_minutes;
    expect(COOLDOWN_RANGE).toEqual({ min: schema.minimum, max: schema.maximum });
  });

  it('turns the old parser examples into visible problems instead of dropping them', () => {
    // parseCountries('ua, gb , xx1, , d') used to keep UA and GB and silently drop the rest.
    const countries = ruleProblems(
      { ...valid, countries: ['UA', 'GB', 'XX1', 'D', 'France'] },
      { knownCountries: known },
    );
    expect(countries.countries).toBe('Remove unknown countries: XX1, D, France.');
    // parseCategories('conflict, bogus') used to keep conflict and drop bogus.
    const categories = ruleProblems(
      { ...valid, categoryMode: 'specific', categories: ['conflict', 'bogus'] },
      { knownCountries: known },
    );
    expect(categories.categories).toBe('Remove unknown categories: bogus.');
  });

  it('never treats an empty specific choice as unrestricted', () => {
    const problems = ruleProblems(
      { ...valid, countries: [], categoryMode: 'specific', categories: [] },
      { knownCountries: known },
    );
    expect(problems.countries).toMatch(/Choose at least one country, or choose Worldwide/);
    expect(problems.categories).toMatch(/Choose at least one category, or choose All/);
    expect(
      ruleProblems(
        { ...valid, locationMode: 'worldwide', countries: [] },
        {
          knownCountries: known,
        },
      ),
    ).toEqual({});
  });

  it('flags overlong and excessive keywords and out-of-range numbers', () => {
    const long = 'x'.repeat(61);
    const many = Array.from({ length: 21 }, (_, index) => `word${String(index)}`).join(', ');
    expect(ruleProblems({ ...valid, keywords: long }, { knownCountries: known }).keywords).toBe(
      'Shorten each keyword to 60 characters or fewer (1 is longer).',
    );
    expect(ruleProblems({ ...valid, keywords: many }, { knownCountries: known }).keywords).toBe(
      'Use at most 20 keywords (21 entered).',
    );
    const numbers = ruleProblems(
      { ...valid, threshold: '0', cooldown: '1441', severityFloor: '2', name: ' ' },
      { knownCountries: known },
    );
    expect(Object.keys(numbers).sort()).toEqual([
      'cooldown_minutes',
      'name',
      'severity_floor',
      'threshold',
    ]);
  });

  it('round-trips every saved value, including the ones the form does not edit', () => {
    const fields = ruleFieldsFromIndicator({ ...indicator, severity_floor: 0.4 });
    const request = ruleRequest(fields, { teamId: '', bbox: undefined, geometry: undefined });
    expect(request).toEqual({
      name: 'Kharkiv strikes',
      description: '',
      countries: ['UA'],
      categories: ['conflict'],
      keywords: ['Kharkiv', 'shelling'],
      threshold: 2,
      window_minutes: 360,
      cooldown_minutes: 60,
      severity_floor: 0.4,
      report_template: 'intsum',
      enabled: true,
    });
  });

  it('summarises what the rule will watch in plain words', () => {
    const summary = ruleSummary(
      { ...valid, keywords: 'Sumy, strike', countries: ['UA'], template: 'intsum' },
      {
        countryName: (code) => (code === 'UA' ? 'Ukraine' : code),
        templateName: () => 'INTSUM',
        bbox: undefined,
      },
    );
    expect(Object.fromEntries(summary.map((row) => [row.label, row.text]))).toEqual({
      Geography: 'Ukraine (UA)',
      Categories: 'All event categories',
      Keywords: 'Title or summary contains any of: “Sumy”, “strike” (literal, not case sensitive)',
      Threshold: '1 or more matching items',
      'Time window': 'The last 6 hours',
      'Severity floor': 'None: every item counts, including unrated ones',
      Cooldown: '1 hour between alerts',
      Report: 'Generates INTSUM when it fires',
    });
  });

  it('splits keywords without dropping overlong entries', () => {
    expect(splitKeywords(' a, , b ,a ')).toEqual(['a', 'b']);
  });
});
