import { describe, expect, it } from 'vitest';

import { areaIndicator, briefSummary } from '@/test/handlers.watches';
import { plan } from '@/test/fixtures.direction';
import { annotationMonitor } from '@/test/fixtures.monitors';
import { schedule } from '@/test/fixtures.schedules';
import { indicator } from '@/test/fixtures.warning';

import {
  WATCH_GROUPS,
  countLabel,
  isAreaWatch,
  mostRecent,
  summariseAlertRules,
  summariseAreaWatches,
  summariseBriefs,
  summariseMonitors,
  summarisePlans,
  summariseSubscriptions,
} from './watchModel';

const label = (teamId: string | null | undefined) => (teamId ? 'Team: Blue' : 'Personal');
const TEAM = '9a9a9a9a-9a9a-49a9-89a9-9a9a9a9a9a9a';

describe('watch model', () => {
  it('explains every kind of watch and links to its full page', () => {
    expect(WATCH_GROUPS.map((group) => group.kind)).toEqual([
      'subscriptions',
      'alertRules',
      'areaWatches',
      'plans',
      'briefs',
      'monitors',
    ]);
    for (const group of WATCH_GROUPS) {
      expect(group.explanation.length).toBeGreaterThan(20);
      expect(group.href.startsWith('/')).toBe(true);
    }
  });

  it('keeps the three newest rows and sorts unreadable dates last', () => {
    const rows = ['2026-09-01', 'not a date', '2026-09-04', '2026-09-03', '2026-09-02'];
    expect(mostRecent(rows, (row) => row)).toEqual(['2026-09-04', '2026-09-03', '2026-09-02']);
  });

  it('describes paused subscriptions and team ownership', () => {
    const result = summariseSubscriptions(
      [schedule, { ...schedule, id: 'paused', name: 'Paused', enabled: false, team_id: TEAM }],
      label,
    );
    expect(result.count).toBe(2);
    expect(result.items.map((item) => item.detail)).toEqual([
      'Personal · next run 6 Sept 2026, 06:00 UTC',
      'Team: Blue · paused',
    ]);
  });

  it('splits indicators into alert rules and area watches', () => {
    const exact = {
      ...areaIndicator,
      id: 'exact',
      bbox: null,
      research_area: { sha256: 'a'.repeat(64), geometry: {} },
      enabled: false,
    } as unknown as typeof areaIndicator;
    expect(isAreaWatch(indicator)).toBe(false);
    expect(isAreaWatch(exact)).toBe(true);
    const rows = [indicator, areaIndicator, exact, { ...indicator, id: 'off', enabled: false }];
    const rules = summariseAlertRules(rows, label);
    expect(rules.count).toBe(2);
    expect(rules.items.map((item) => item.detail)).toEqual([
      'Personal · 2 or more in 6 h',
      'Personal · switched off',
    ]);
    const areas = summariseAreaWatches(rows, label);
    expect(areas.count).toBe(2);
    expect(areas.items.map((item) => item.detail).sort()).toEqual([
      'Personal · map rectangle',
      'Personal · switched off',
    ]);
  });

  it('counts plan requirements and links each plan', () => {
    const result = summarisePlans([plan], label);
    expect(result.items[0]).toMatchObject({
      label: plan.name,
      to: `/direction/plans/${plan.id}`,
    });
    expect(result.items[0]?.detail).toMatch(/^Personal · 1 PIR, \d+ SIR$/);
  });

  it('marks a full page of briefs as possibly more and uses the monitor total', () => {
    const briefs = summariseBriefs({ items: [briefSummary], limit: 1 }, label);
    expect(countLabel(briefs)).toBe('1+');
    expect(briefs.items[0]?.to).toBe(`/research?brief=${briefSummary.id}&revision=4`);
    expect(countLabel(summariseBriefs({ items: [], limit: 50 }, label))).toBe('0');
    const monitors = summariseMonitors(
      { items: [{ ...annotationMonitor, status: 'paused' }], total: 7 },
      label,
    );
    expect(countLabel(monitors)).toBe('7');
    expect(monitors.items[0]?.detail).toBe('Personal · paused');
  });
});
