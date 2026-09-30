import { expect, it } from 'vitest';
import { conflictCard, conflictDetail } from '@/test/fixtures';
import { conflictCardSchema, conflictDetailSchema, conflictSourceSchema } from './trackers';

it('defaults legacy response additions while keeping unknown fatalities nullable', () => {
  const legacy = {
    ...conflictCard,
    fatalities_7d: undefined,
    fatalities_upper_7d: undefined,
    fatalities_unknown_incidents: undefined,
    fatalities_disputed_incidents: undefined,
    other_activity_7d: undefined,
    unknown_date_reports: undefined,
    collapsed_reports_7d: undefined,
  };
  expect(conflictCardSchema.parse(legacy)).toMatchObject({
    fatalities_7d: null,
    fatalities_upper_7d: null,
    fatalities_unknown_incidents: 0,
    fatalities_disputed_incidents: 0,
    other_activity_7d: 0,
    unknown_date_reports: 0,
    collapsed_reports_7d: 0,
  });
  expect(
    conflictDetailSchema.parse({ ...conflictDetail, evidence_groups: undefined }).evidence_groups,
  ).toEqual([]);
});

it('rejects negative incident counts and unsupported source statuses', () => {
  expect(
    conflictCardSchema.safeParse({ ...conflictCard, fatalities_unknown_incidents: -1 }).success,
  ).toBe(false);
  expect(
    conflictSourceSchema.safeParse({
      id: 'source',
      name: 'Source',
      role: 'Current',
      status: 'secret_error',
      detail: '',
      dataset_release: null,
      last_success: null,
    }).success,
  ).toBe(false);
});
