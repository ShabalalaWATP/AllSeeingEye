import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import {
  conflictKind,
  conflictReportLabel,
  countConflictReports,
  filterConflictReports,
} from './conflicts';

const protest = liveEvent({ id: 'protest', category: 'conflict', subtype: 'protest' });
const riot = liveEvent({ id: 'riot', category: 'conflict', subtype: 'riot' });
const unrest = liveEvent({
  id: 'unspecified',
  category: 'conflict',
  subtype: 'fight',
  attributes: { conflict_screening: 'llm', conflict_relevance: 'civil_unrest' },
});

it('separates source-labelled riots from protests and unspecified screened unrest', () => {
  expect(conflictKind(protest)).toBe('protests');
  expect(conflictKind(riot)).toBe('riots');
  expect(conflictKind(unrest)).toBe('unrest');
  expect(countConflictReports([protest, riot, unrest])).toMatchObject({
    all: 3,
    protests: 1,
    riots: 1,
    unrest: 1,
  });
  expect(filterConflictReports([protest, riot, unrest], 'protests')).toEqual([protest]);
  expect(filterConflictReports([protest, riot, unrest], 'riots')).toEqual([riot]);
  expect(filterConflictReports([protest, riot, unrest], 'unrest')).toEqual([unrest]);
});

it('retains provider protest or riot detail within broad screened unrest without claiming all protests are violent', () => {
  for (const event of [protest, riot]) {
    const assessed = {
      ...event,
      attributes: { conflict_screening: 'llm', conflict_relevance: 'civil_unrest' },
    };
    expect(conflictKind(assessed)).toBe(conflictKind(event));
  }
  expect(conflictReportLabel(protest)).toBe('Protests / demonstrations');
  expect(
    conflictKind({
      ...protest,
      attributes: { sub_event_type: 'Excessive force against protesters' },
    }),
  ).toBe('protests');
  expect(conflictKind(liveEvent({ ...protest, title: 'Violent riots after strike' }))).toBe(
    'protests',
  );
});

it('never brings unrelated accidents, pending or uncertain media back through unrest filters', () => {
  const items = ['unrelated', 'context', 'uncertain'].map((conflict_relevance) =>
    liveEvent({
      ...riot,
      id: conflict_relevance,
      source_id: 'gdelt_events',
      attributes: { conflict_screening: 'llm', conflict_relevance },
    }),
  );
  expect(filterConflictReports(items, 'all')).toEqual([]);
  expect(filterConflictReports(items, 'riots', false, true).map((event) => event.id)).toEqual([
    'uncertain',
  ]);
  expect(filterConflictReports(items, 'protests', false, true)).toEqual([]);
});

it.each(['145', '1451', '1452', '1453', '1454'])(
  'uses explicit GDELT CAMEO %s for riots while preserving raw classification and screening',
  (event_code) => {
    const raw = liveEvent({ ...protest, source_id: 'gdelt_events', attributes: { event_code } });
    expect(conflictKind(raw)).toBe('riots');
    expect(raw.subtype).toBe('protest');
    expect(filterConflictReports([raw], 'riots')).toEqual([]);
    const screened = {
      ...raw,
      attributes: { event_code, conflict_screening: 'llm', conflict_relevance: 'civil_unrest' },
    };
    expect(filterConflictReports([screened], 'riots')).toEqual([screened]);
    expect(
      conflictKind({
        ...screened,
        attributes: { ...screened.attributes, conflict_relevance: 'armed_conflict' },
      }),
    ).toBe('organised_violence');
    const rejected = {
      ...screened,
      attributes: { ...screened.attributes, conflict_relevance: 'unrelated' },
    };
    expect(filterConflictReports([rejected], 'riots', true, true)).toEqual([]);
  },
);

it.each(['14', '140', '141', '144', '1455', '14599', 'violence', '', 145, null])(
  'does not invent violent protest from unspecified or invalid event code %s',
  (event_code) => {
    expect(
      conflictKind(
        liveEvent({ ...protest, source_id: 'gdelt_events', attributes: { event_code } }),
      ),
    ).toBe('protests');
  },
);

it('does not apply GDELT codes to other sources', () => {
  expect(
    conflictKind(
      liveEvent({ ...protest, source_id: 'acled_events', attributes: { event_code: '145' } }),
    ),
  ).toBe('protests');
});
