import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import {
  conflictKind,
  conflictReportLabel,
  countConflictReports,
  filterConflictReports,
  isHistoricalConflict,
} from './conflicts';

it('recognises explicitly tagged historical reports without hiding unrelated overlays', () => {
  const historical = liveEvent({ category: 'conflict', tags: ['provisional_monthly'] });
  const other = liveEvent({ category: 'news', tags: ['provisional_monthly'] });
  expect(isHistoricalConflict(historical)).toBe(true);
  expect(isHistoricalConflict(other)).toBe(false);
  expect(filterConflictReports([historical, other], 'all')).toEqual([other]);
  expect(filterConflictReports([historical, other], 'all', true)).toEqual([historical, other]);
});

it.each([
  ['fight', 'armed_clashes'],
  ['armed_clash', 'armed_clashes'],
  ['battle', 'armed_clashes'],
  ['organised_violence', 'organised_violence'],
  ['strike', 'strikes'],
  ['explosion', 'strikes'],
  ['civilian_harm', 'civilian_harm'],
  ['violence_against_civilians', 'civilian_harm'],
  ['mass_violence', 'civilian_harm'],
  ['protest', 'protests'],
  ['riot', 'protests'],
  ['force_posture', 'military_activity'],
  ['coercion', 'other'],
  ['assault', 'other'],
  ['unknown', 'other'],
  ['__proto__', 'other'],
  ['constructor', 'other'],
  [' Armed-Clash ', 'armed_clashes'],
])('classifies provider subtype %s without title or tag inference', (subtype, expected) => {
  expect(
    conflictKind(
      liveEvent({ category: 'conflict', subtype, title: 'War strikes protest', tags: ['battle'] }),
    ),
  ).toBe(expected);
});

it('keeps non-conflict overlays intact, counts reports once and preserves stable unfiltered data', () => {
  const clash = liveEvent({ id: 'clash', category: 'conflict', subtype: 'fight' });
  const protest = liveEvent({ id: 'protest', category: 'conflict', subtype: 'protest' });
  const plane = liveEvent({ id: 'plane', category: 'aviation', subtype: 'battle' });
  const events = [clash, protest, plane];
  expect(filterConflictReports(events, 'all')).toBe(events);
  expect(filterConflictReports(events, 'armed_clashes')).toEqual([clash, plane]);
  expect(filterConflictReports(events, 'protests')).toEqual([protest, plane]);
  expect(conflictKind(plane)).toBeNull();
  expect(conflictReportLabel(protest)).toBe('Protests and riots');
  expect(conflictReportLabel(plane)).toBe('Other report');
  expect(countConflictReports(events)).toEqual({
    all: 2,
    armed_clashes: 1,
    organised_violence: 0,
    protests: 1,
    strikes: 0,
    civilian_harm: 0,
    military_activity: 0,
    other: 0,
  });
});
