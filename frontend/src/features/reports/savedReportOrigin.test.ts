import { describe, expect, it } from 'vitest';

import type { ReportSummary } from '@/lib/api/reports';

import { reportOrigin, savedPathFor } from './savedReportOrigin';

const report = (scope: Record<string, unknown>) => ({ scope }) as unknown as ReportSummary;

describe('saved report origin', () => {
  it('returns automatic briefings to the workspace that prepared them', () => {
    expect(savedPathFor(report({ origin: 'briefing', briefing: 'daily' }))).toBe('/trackers');
    expect(savedPathFor(report({ origin: 'briefing', briefing: 'economy' }))).toBe('/economy');
    expect(savedPathFor(report({ origin: 'briefing', briefing: 'cyber' }))).toBe('/cyber');
    expect(savedPathFor(report({ origin: 'briefing', briefing: 'other' }))).toBe(
      '/research/jobs?briefings=1',
    );
  });

  it('keeps requested research, subscriptions and geolocation in their saved sections', () => {
    expect(savedPathFor(report({ origin: 'research' }))).toBe('/research/saved');
    expect(savedPathFor(report({ origin: 'subscription' }))).toBe('/subscriptions/saved');
    expect(savedPathFor(report({ research_focus: 'media' }))).toBe('/geolocation/saved');
    expect(reportOrigin(report({ briefing: 'daily' }))).toBe('research');
    expect(savedPathFor(null)).toBe('/research/saved');
  });
});
