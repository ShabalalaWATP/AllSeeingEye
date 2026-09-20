import proj4 from 'proj4';
import type { Position } from './geoJsonTypes';
import { measurementPoint } from './measurements';

export interface UtmCoordinate {
  zone: number;
  hemisphere: 'N' | 'S';
  easting: number;
  northing: number;
}
const utmDefinition = (zone: number, hemisphere: 'N' | 'S') =>
  `+proj=utm +zone=${zone} ${hemisphere === 'S' ? '+south' : ''} +datum=WGS84 +units=m +no_defs`;

export function parseCoordinate(text: string, axis: 'latitude' | 'longitude'): number {
  if (text.length > 100) throw new Error('Coordinate input is too long.');
  const input = text.trim().toUpperCase();
  const limit = axis === 'latitude' ? 90 : 180;
  let value: number;
  if (/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(input)) value = Number(input);
  else {
    const normal = input
      .replace(/[°'′"″]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
    const match = /^(\d+(?:\.\d+)?)(?: (\d+(?:\.\d+)?))?(?: (\d+(?:\.\d+)?))? ?([NSEW])$/.exec(
      normal,
    );
    if (!match)
      throw new Error(
        `Enter ${axis} as decimal degrees or degrees, minutes and seconds with a hemisphere.`,
      );
    const degrees = Number(match[1]),
      minutes = Number(match[2] ?? 0),
      seconds = Number(match[3] ?? 0);
    const hemisphere = match[4] ?? '';
    if (!(axis === 'latitude' ? 'NS' : 'EW').includes(hemisphere))
      throw new Error(`Use ${axis === 'latitude' ? 'N or S' : 'E or W'} for ${axis}.`);
    if (
      minutes >= 60 ||
      seconds >= 60 ||
      (match[2] && !Number.isInteger(degrees)) ||
      (match[3] && !Number.isInteger(minutes))
    )
      throw new Error(
        'Minutes and seconds must be below 60; only the final component may contain a fraction.',
      );
    value = (degrees + minutes / 60 + seconds / 3600) * ('SW'.includes(hemisphere) ? -1 : 1);
  }
  if (!Number.isFinite(value) || Math.abs(value) > limit)
    throw new Error(
      `${axis === 'latitude' ? 'Latitude' : 'Longitude'} must be from -${limit} to ${limit}.`,
    );
  return value;
}

export function parseCoordinatePair(latitude: string, longitude: string): Position {
  return [parseCoordinate(longitude, 'longitude'), parseCoordinate(latitude, 'latitude')];
}

export function formatDms(value: number, axis: 'latitude' | 'longitude'): string {
  const seconds = Math.round(Math.abs(value) * 360000) / 100;
  const degrees = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds - degrees * 3600) / 60);
  const remainder = seconds - degrees * 3600 - minutes * 60;
  return `${degrees}° ${minutes}′ ${remainder.toFixed(2)}″ ${axis === 'latitude' ? (value < 0 ? 'S' : 'N') : value < 0 ? 'W' : 'E'}`;
}

export function toUtm(position: Position): UtmCoordinate | null {
  const [lon, lat] = measurementPoint(...position);
  if (lat < -80 || lat > 84) return null;
  let zone = Math.min(60, Math.floor((lon + 180) / 6) + 1);
  if (lat >= 56 && lat < 64 && lon >= 3 && lon < 12) zone = 32;
  if (lat >= 72 && lat <= 84 && lon >= 0 && lon < 42)
    zone = lon < 9 ? 31 : lon < 21 ? 33 : lon < 33 ? 35 : 37;
  const hemisphere = lat < 0 ? 'S' : 'N';
  const [easting, northing] = proj4('EPSG:4326', utmDefinition(zone, hemisphere), position);
  return { zone, hemisphere, easting, northing };
}

export function fromUtm(value: UtmCoordinate): Position {
  const { zone, hemisphere, easting, northing } = value;
  if (
    !Number.isInteger(zone) ||
    zone < 1 ||
    zone > 60 ||
    !['N', 'S'].includes(hemisphere) ||
    !Number.isFinite(easting) ||
    easting < 100000 ||
    easting > 900000 ||
    !Number.isFinite(northing) ||
    northing < 0 ||
    northing > 10000000
  )
    throw new Error(
      'Use UTM zone 1–60, hemisphere N/S, easting 100,000–900,000 m and northing 0–10,000,000 m.',
    );
  const [lon, lat] = proj4(utmDefinition(zone, hemisphere), 'EPSG:4326', [easting, northing]);
  const point = measurementPoint(lon, lat);
  if (
    point[1] < -80 ||
    point[1] > 84 ||
    (hemisphere === 'N' && point[1] < -0.000001) ||
    (hemisphere === 'S' && point[1] > 0.000001)
  )
    throw new Error(
      'These coordinates fall outside the selected UTM hemisphere or latitude coverage.',
    );
  return point;
}
