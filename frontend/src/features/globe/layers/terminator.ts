/**
 * The day and night terminator: the sun's subsolar point from the clock, the great
 * circle ninety degrees from it, and the night hemisphere as one translucent polygon.
 * Accuracy is a fraction of a degree, which is all a globe overlay needs.
 */
import { SolidPolygonLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';

export interface SunPosition {
  lon: number;
  lat: number;
}

export type Ring = [number, number][];

export const TERMINATOR_LAYER_ID = 'terminator';
const NIGHT_FILL: [number, number, number, number] = [4, 8, 24, 120];
const MS_PER_DAY = 86_400_000;
/** Days from the Unix epoch to J2000.0 (2000-01-01 12:00 UTC). */
const J2000_OFFSET_DAYS = 10957.5;
const POLE_LATITUDE = 89.9;

const toRadians = (degrees: number) => (degrees * Math.PI) / 180;
const toDegrees = (radians: number) => (radians * 180) / Math.PI;
const wrapLongitude = (degrees: number) => ((((degrees + 180) % 360) + 360) % 360) - 180;

/** Where the sun is directly overhead at `date` (low-precision solar position). */
export function subsolarPoint(date: Date): SunPosition {
  const days = date.getTime() / MS_PER_DAY - J2000_OFFSET_DAYS;
  const meanLongitude = 280.46 + 0.9856474 * days;
  const meanAnomaly = toRadians(357.528 + 0.9856003 * days);
  const eclipticLongitude = toRadians(
    meanLongitude + 1.915 * Math.sin(meanAnomaly) + 0.02 * Math.sin(2 * meanAnomaly),
  );
  const obliquity = toRadians(23.439 - 0.0000004 * days);
  const declination = Math.asin(Math.sin(obliquity) * Math.sin(eclipticLongitude));
  const rightAscension = Math.atan2(
    Math.cos(obliquity) * Math.sin(eclipticLongitude),
    Math.cos(eclipticLongitude),
  );
  const siderealTime = 280.46061837 + 360.98564736629 * days;
  return {
    lon: wrapLongitude(toDegrees(rightAscension) - siderealTime),
    lat: toDegrees(declination),
  };
}

/** The night hemisphere as a ring: the terminator curve closed over the dark pole. */
export function nightPolygon(sun: SunPosition, stepDegrees = 2): Ring {
  const declination = toRadians(Math.abs(sun.lat) < 1e-6 ? 1e-6 : sun.lat);
  const tanDeclination = Math.tan(declination);
  const ring: Ring = [];
  for (let lon = -180; lon <= 180; lon += stepDegrees) {
    const lat = toDegrees(Math.atan(-Math.cos(toRadians(lon - sun.lon)) / tanDeclination));
    ring.push([lon, lat]);
  }
  // When the sun sits north of the equator the south pole is in darkness, and vice versa.
  const darkPole = sun.lat > 0 ? -POLE_LATITUDE : POLE_LATITUDE;
  ring.push([180, darkPole], [-180, darkPole]);
  return ring;
}

export function buildTerminatorLayer(date: Date): Layer {
  const ring = nightPolygon(subsolarPoint(date));
  return new SolidPolygonLayer<{ ring: Ring }>({
    id: TERMINATOR_LAYER_ID,
    data: [{ ring }],
    getPolygon: (night) => night.ring,
    getFillColor: NIGHT_FILL,
    filled: true,
    extruded: false,
    pickable: false,
  });
}
