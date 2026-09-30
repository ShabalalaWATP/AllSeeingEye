import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import {
  isMilitaryAircraft,
  isMilitaryVessel,
  militaryTrafficLabel,
  trafficSearchText,
  MILITARY_AIRCRAFT_COLOUR,
  MILITARY_VESSEL_COLOUR,
} from './traffic';
import { buildIconLayer } from '@/features/globe/layers/icons';

it('classifies only explicit military provider data, including AIS ship type35', () => {
  const aircraft = liveEvent({ category: 'aviation', attributes: { military: true } });
  const vessel = liveEvent({
    category: 'maritime',
    subtype: 'vessel_position',
    attributes: { ship_type_code: 35 },
  });
  expect(isMilitaryAircraft(aircraft)).toBe(true);
  expect(isMilitaryVessel(vessel)).toBe(true);
  expect(isMilitaryAircraft(vessel)).toBe(false);
  expect(isMilitaryVessel(aircraft)).toBe(false);
  expect(
    isMilitaryAircraft(liveEvent({ category: 'aviation', title: 'RAF military aircraft' })),
  ).toBe(false);
  expect(isMilitaryVessel({ ...vessel, attributes: {}, tags: [], title: 'USS Military' })).toBe(
    false,
  );
  expect(militaryTrafficLabel(vessel)).toBe('Reported military operations');
  expect(militaryTrafficLabel(liveEvent())).toBeNull();
});

it.each([false, true])(
  'keeps military colours distinct from ordinary traffic in globe=%s',
  (globe) => {
    const aircraft = liveEvent({
      id: 'mil-air',
      category: 'aviation',
      subtype: 'military_aircraft',
    });
    const vessel = liveEvent({
      id: 'mil-ship',
      category: 'maritime',
      subtype: 'vessel_position',
      tags: ['military'],
    });
    const plain = liveEvent({ id: 'civil', category: 'aviation' });
    const layer = buildIconLayer([aircraft, vessel, plain], () => undefined, aircraft.id, globe);
    const colour = (
      layer?.props as unknown as { getColor: (event: typeof aircraft) => readonly number[] }
    ).getColor;
    expect(colour(aircraft)).toEqual(MILITARY_AIRCRAFT_COLOUR);
    expect(colour(vessel)).toEqual(MILITARY_VESSEL_COLOUR);
    expect(colour(plain)).not.toEqual(colour(aircraft));
    expect(colour({ ...aircraft, subtype: 'emergency' })).toEqual([255, 90, 90, 255]);
  },
);

it('indexes provider identifiers without needing a title match', () => {
  expect(
    trafficSearchText(
      liveEvent({ attributes: { icao24: 'ABCDEF', mmsi: 123456789, registration: 'G-TEST' } }),
    ),
  ).toContain('abcdef');
  expect(trafficSearchText(liveEvent({ attributes: { registration: 'G-TEST' } }))).toContain(
    'g-test',
  );
});
