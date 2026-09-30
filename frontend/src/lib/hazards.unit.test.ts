import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import {
  countFires,
  countHazards,
  DEFAULT_HAZARD_OPTIONS,
  hazardFiltersRefined,
  hazardKind,
  matchesHazard,
} from './hazards';

// EONET _snake(category.id) contract; the saved EONET fixture contains wildfires
// and severeStorms. Additional categories retain their explicit provider names.
it.each([
  ['wildfires', 'wildfire'],
  ['severe_storms', 'weather'],
  ['earthquakes', 'earthquake'],
  ['floods', 'flood'],
  ['volcanoes', 'volcano'],
  ['landslides', 'landslide'],
  ['sea_lake_ice', 'ice'],
  ['tropical_cyclone', 'weather'],
  ['volcano', 'volcano'],
  ['thermal_detection', 'thermal'],
] as const)('maps concrete adapter subtype %s to %s', (subtype, group) => {
  const event = liveEvent({ category: 'disaster', subtype });
  expect(hazardKind(event)).toBe(group);
  if (group === 'wildfire' || group === 'thermal') {
    expect(matchesHazard(event, { ...DEFAULT_HAZARD_OPTIONS, groups: [] }, Date.now())).toBe(true);
    expect(countFires([event])[group]).toBe(1);
    expect(countHazards([event]).all).toBe(0);
  } else {
    expect(matchesHazard(event, { ...DEFAULT_HAZARD_OPTIONS, groups: [group] }, Date.now())).toBe(
      true,
    );
    expect(countHazards([event])[group]).toBe(1);
  }
});

it('combines selected natural types without filtering fire records and recognises restored defaults by value', () => {
  const events = ['earthquake', 'flood', 'volcano', 'wildfire', 'thermal_detection'].map(
    (subtype) => liveEvent({ id: subtype, category: 'disaster', subtype }),
  );
  const options = { ...DEFAULT_HAZARD_OPTIONS, groups: ['earthquake', 'flood'] as const };
  expect(
    events.filter((event) => matchesHazard(event, options, Date.now())).map((event) => event.id),
  ).toEqual(['earthquake', 'flood', 'wildfire', 'thermal_detection']);
  expect(hazardFiltersRefined(options)).toBe(true);
  expect(
    hazardFiltersRefined({
      ...DEFAULT_HAZARD_OPTIONS,
      groups: [...DEFAULT_HAZARD_OPTIONS.groups].reverse(),
    }),
  ).toBe(false);
  expect(hazardFiltersRefined({ ...DEFAULT_HAZARD_OPTIONS, hours: '24' })).toBe(true);
  expect(hazardFiltersRefined({ ...DEFAULT_HAZARD_OPTIONS, minimumMagnitude: 4 })).toBe(true);
  expect(hazardFiltersRefined({ ...DEFAULT_HAZARD_OPTIONS, alert: 'red' })).toBe(true);
  expect(hazardFiltersRefined({ ...DEFAULT_HAZARD_OPTIONS, includeUnknown: false })).toBe(true);
});

it('applies magnitude to EONET earthquakes without mistaking other measurement units for magnitude', () => {
  const quake = liveEvent({
    category: 'disaster',
    subtype: 'earthquakes',
    attributes: { magnitude_value: 7, magnitude_unit: 'unknown' },
  });
  expect(
    matchesHazard(
      quake,
      { ...DEFAULT_HAZARD_OPTIONS, minimumMagnitude: 4, includeUnknown: false },
      Date.now(),
    ),
  ).toBe(false);
  expect(matchesHazard(quake, { ...DEFAULT_HAZARD_OPTIONS, minimumMagnitude: 4 }, Date.now())).toBe(
    true,
  );
});

it('keeps unknown category strings and unrelated reports honest without substring guessing', () => {
  for (const subtype of [
    'wildfires_unconfirmed',
    'iceberg_military',
    'not_a_volcano',
    'storm_warning_other',
  ]) {
    expect(hazardKind(liveEvent({ category: 'disaster', subtype }))).toBe('other');
  }
  expect(hazardKind(liveEvent({ category: 'news', subtype: 'wildfires' }))).toBeNull();
});
