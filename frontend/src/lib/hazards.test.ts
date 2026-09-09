import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { countHazards, DEFAULT_HAZARD_OPTIONS, hazardKind, matchesHazard } from './hazards';

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
  expect(matchesHazard(event, { ...DEFAULT_HAZARD_OPTIONS, group }, Date.now())).toBe(true);
  expect(countHazards([event])[group]).toBe(1);
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
