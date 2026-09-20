import { z } from 'zod';
export type RfSiteKind = 'origin' | 'receiver';
export type RfSiteNames = Record<RfSiteKind, string>;
export const rfPositionSchema = z.tuple([
  z.number().min(-180).max(180),
  z.number().min(-90).max(90),
]);
/** Decimal or explicit degrees/minutes/seconds, with hemisphere checked against the axis. */
export function parseSiteCoordinate(raw: string, axis: 'latitude' | 'longitude'): number {
  const text = raw.trim().toUpperCase();
  const decimal = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/;
  let value: number;
  if (decimal.test(text)) value = Number(text);
  else {
    const match =
      /^(\d{1,3})(?:°|\s+)\s*(\d{1,2})(?:['′]|\s+)\s*(\d{1,2}(?:\.\d+)?)(?:["″])?\s*([NSEW])$/.exec(
        text,
      );
    if (!match)
      throw new Error('Use decimal degrees or degrees minutes seconds with N, S, E or W.');
    const [, degrees, minutes, seconds, hemisphere] = match;
    if (
      Number(minutes) >= 60 ||
      Number(seconds) >= 60 ||
      !(axis === 'latitude' ? /[NS]/ : /[EW]/).test(hemisphere ?? '')
    )
      throw new Error('Check minutes, seconds and the coordinate hemisphere.');
    value =
      (Number(degrees) + Number(minutes) / 60 + Number(seconds) / 3600) *
      (/[SW]/.test(hemisphere ?? '') ? -1 : 1);
  }
  const limit = axis === 'latitude' ? 90 : 180;
  if (!Number.isFinite(value) || Math.abs(value) > limit)
    throw new Error(`${axis}: enter a value between -${limit} and ${limit}.`);
  return value;
}
