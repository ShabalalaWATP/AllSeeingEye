import { afterEach, describe, expect, it, vi } from 'vitest';
import { report } from '@/test/fixtures.reports';
import { followUpAvailability, followUpRequest } from './followUpScope';

const area = {
  geometry: {
    type: 'Polygon',
    coordinates: [
      [
        [0, 0],
        [1, 0],
        [0, 1],
        [0, 0],
      ],
    ],
  },
  sha256: 'a'.repeat(64),
};
const period = { research_since: '2020-01-01T00:00:00Z', research_until: '2021-01-01T00:00:00Z' };
function parent(scope: Record<string, unknown>, version = 1) {
  return {
    ...report,
    report: { ...report.report, scope },
    version: { ...report.version, number: version },
  };
}
afterEach(() => vi.useRealTimers());

describe('restoring exact follow-up scope', () => {
  it.each([0, -1, 1.5, Number.MAX_SAFE_INTEGER + 1])(
    'refuses invalid version %s before starting',
    (version) => {
      expect(followUpAvailability(parent({}, version))).toMatchObject({
        request: null,
        reason: expect.stringContaining('version is invalid'),
      });
    },
  );

  it.each([
    [{ research_area: area, map_origin: { area } }, 'ambiguous'],
    [{ research_area: area, research_focus: 'company' }, 'report type'],
    [{ research_area: area, research_focus: 'general' }, 'disclosure is missing'],
    [
      { research_area: area, research_focus: 'general', disclose_area_to_provider: true },
      'fixed area period is missing',
    ],
    [{ research_time_basis: 'recorded_time' }, 'recorded-time period is missing'],
    [{ window_hours: 0 }, 'reporting window is invalid'],
    [{ window_hours: 730 * 24 + 1 }, 'reporting window is invalid'],
  ])('refuses incomplete saved scope %j', (scope, reason) => {
    expect(followUpAvailability(parent(scope))).toMatchObject({
      request: null,
      reason: expect.stringContaining(reason),
    });
  });

  it.each([
    { research_since: '2021-01-01T00:00:00Z' },
    { research_until: '2021-01-01T00:00:00Z' },
    { research_since: '2022-01-01T00:00:00Z', research_until: '2021-01-01T00:00:00Z' },
  ])('rejects incomplete or reversed recorded periods %j', (scope) => {
    expect(
      followUpAvailability(parent({ ...scope, research_time_basis: 'recorded_time' })),
    ).toMatchObject({
      request: null,
      reason: expect.stringContaining('valid recorded period'),
    });
  });

  it('rejects oversized and future recorded periods but preserves a valid historical interval', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-09-30T00:00:00Z'));
    const basis = { research_time_basis: 'recorded_time' };
    expect(
      followUpAvailability(
        parent({
          ...basis,
          research_since: '1980-01-01T00:00:00Z',
          research_until: period.research_until,
        }),
      ).reason,
    ).toContain('cannot exceed 30 years');
    expect(
      followUpAvailability(
        parent({
          ...basis,
          research_since: period.research_since,
          research_until: '2027-01-01T00:00:00Z',
        }),
      ).reason,
    ).toContain('cannot end in the future');
    const result = followUpRequest(parent({ ...basis, ...period }));
    expect(result).toMatchObject({ ...basis, ...period });
    expect(result).not.toHaveProperty('window_hours');
  });

  it('retains exact area, publication interval and explicit empty source selections', () => {
    const scope = {
      ...period,
      map_origin: { area },
      research_focus: 'general',
      disclose_area_to_provider: true,
      research_source_ids: [],
      research_terms: [],
      research_query_variants: [],
      research_candidate_hypotheses: [],
      research_planned_tasks: [],
    };
    expect(followUpRequest(parent(scope))).toMatchObject({
      ...period,
      research_area: { geometry: area.geometry },
      disclose_area_to_provider: true,
      research_source_ids: [],
      research_terms: [],
      research_query_variants: [],
      research_candidate_hypotheses: [],
      research_planned_tasks: [],
    });
  });

  it('shows a safe validation reason for malformed stored scope', () => {
    expect(
      followUpAvailability(parent({ research_area: { geometry: {}, sha256: 'invalid' } })),
    ).toEqual({
      request: null,
      reason: 'The saved scope cannot be safely restored for a follow-up.',
    });
  });
});
