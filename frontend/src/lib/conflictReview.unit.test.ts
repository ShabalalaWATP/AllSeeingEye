import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import {
  conflictReview,
  isUnreviewedConflictSignal,
  matchesConflictReview,
} from './conflictReview';
import { filterConflictReports } from './conflicts';

const pending = liveEvent({ category: 'conflict', source_id: 'gdelt_events', subtype: 'fight' });

it('requires screening for GDELT and other machine-coded conflict feeds, without affecting other categories', () => {
  expect(conflictReview(pending)).toMatchObject({
    state: 'pending',
    assessed: false,
    label: 'Unreviewed media signal',
  });
  expect(matchesConflictReview(pending)).toBe(false);
  expect(matchesConflictReview(pending, true)).toBe(true);
  expect(
    matchesConflictReview(liveEvent({ ...pending, source_id: 'other', tags: ['machine_coded'] })),
  ).toBe(false);
  expect(conflictReview(liveEvent({ ...pending, source_id: 'acled_events' }))).toBeNull();
  const news = liveEvent({ ...pending, category: 'news' });
  expect(conflictReview(news)).toBeNull();
  expect(matchesConflictReview(news)).toBe(true);
});

it.each(['armed_conflict', 'civil_unrest', 'military_activity'])(
  'admits %s after model screening without changing its provider type or grade',
  (relevance) => {
    const event = liveEvent({
      ...pending,
      attributes: { conflict_screening: 'llm', conflict_relevance: relevance },
    });
    expect(conflictReview(event)?.state).toBe('accepted');
    expect(isUnreviewedConflictSignal(event)).toBe(false);
    expect(filterConflictReports([event], 'all')).toEqual([event]);
    expect(event.subtype).toBe('fight');
    expect(event.grade).toBe(pending.grade);
    expect(
      matchesConflictReview(liveEvent({ ...event, attributes: { conflict_relevance: relevance } })),
    ).toBe(false);
  },
);

it.each(['unrelated', 'context'])(
  'never reintroduces %s through either map opt-in',
  (relevance) => {
    const event = liveEvent({
      ...pending,
      attributes: {
        conflict_screening: 'llm',
        conflict_relevance: relevance,
        dataset_status: 'provisional_monthly',
      },
    });
    expect(conflictReview(event)?.state).toBe('excluded');
    expect(isUnreviewedConflictSignal(event)).toBe(false);
    expect(filterConflictReports([event], 'all', true, true)).toEqual([]);
    expect(
      matchesConflictReview(
        liveEvent({ ...event, attributes: { conflict_relevance: relevance } }),
        true,
      ),
    ).toBe(false);
  },
);

it('keeps uncertain, missing and malformed model responses behind the separate media opt-in', () => {
  const uncertain = liveEvent({
    ...pending,
    attributes: { conflict_screening: 'llm', conflict_relevance: 'uncertain' },
  });
  expect(conflictReview(uncertain)?.state).toBe('uncertain');
  expect(isUnreviewedConflictSignal(uncertain)).toBe(true);
  for (const relevance of [null, 10, '', '  ', '__proto__', 'constructor', 'invented']) {
    const malformed = liveEvent({
      ...pending,
      attributes: { conflict_screening: 'llm', conflict_relevance: relevance },
    });
    expect(conflictReview(malformed)?.state).toBe('pending');
    expect(matchesConflictReview(malformed)).toBe(false);
  }
  expect(filterConflictReports([pending, uncertain], 'all')).toEqual([]);
  expect(filterConflictReports([pending, uncertain], 'all', false, true)).toEqual([
    pending,
    uncertain,
  ]);
  const historical = liveEvent({
    ...uncertain,
    attributes: { ...uncertain.attributes, dataset_status: 'provisional_monthly' },
  });
  expect(filterConflictReports([historical], 'all', false, true)).toEqual([]);
  expect(filterConflictReports([historical], 'all', true, false)).toEqual([]);
  expect(filterConflictReports([historical], 'all', true, true)).toEqual([historical]);
});

it('extracts only string screening provenance and strips surrounding whitespace', () => {
  expect(
    conflictReview(
      liveEvent({
        ...pending,
        attributes: {
          conflict_screening: 'llm',
          conflict_relevance: 'armed_conflict',
          conflict_screening_reason: '  Armed actors reported.  ',
          conflict_screening_quote: '  Troops exchanged fire. ',
          conflict_screening_model: ' model-name ',
          conflict_screening_source: ' bbc_world ',
        },
      }),
    ),
  ).toMatchObject({
    reason: 'Armed actors reported.',
    quote: 'Troops exchanged fire.',
    model: 'model-name',
    source: 'bbc_world',
  });
  expect(
    conflictReview(
      liveEvent({
        ...pending,
        attributes: {
          conflict_screening_reason: true,
          conflict_screening_quote: '',
          conflict_screening_model: null,
        },
      }),
    ),
  ).toMatchObject({ reason: null, quote: null, model: null, source: null });
});
