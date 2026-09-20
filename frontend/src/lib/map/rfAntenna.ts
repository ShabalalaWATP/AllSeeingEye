import { Geodesic } from 'geographiclib-geodesic';
import type { Position } from './geoJsonTypes';
import type { RfInputs } from './rfPlanning';
export interface RfAntennaDraft {
  enabled: boolean;
  transmitterBearing: string;
  receiverBearing: string;
  beamwidth: string;
  maximumAttenuation: string;
}
export const RF_ANTENNA_DEFAULTS: RfAntennaDraft = {
  enabled: false,
  transmitterBearing: '0',
  receiverBearing: '180',
  beamwidth: '60',
  maximumAttenuation: '20',
};
/** User-defined horizontal parabolic cut. Width is the full -3 dB beamwidth.
 * This idealised pattern is a planning assumption, not an equipment radiation pattern.
 */
export function antennaAttenuation(
  direction: number,
  bearing: number,
  width: number,
  maximum: number,
): number {
  if (
    ![direction, bearing, width, maximum].every(Number.isFinite) ||
    width < 1 ||
    width > 180 ||
    maximum < 0 ||
    maximum > 60 ||
    bearing < 0 ||
    bearing > 360
  )
    throw new Error('Check antenna bearing, beamwidth (1–180°) and maximum attenuation (0–60 dB).');
  const offset = Math.abs(((((direction - bearing + 540) % 360) + 360) % 360) - 180);
  return Math.min(maximum, 12 * (offset / width) ** 2);
}
export function directionalRfInputs(
  input: RfInputs,
  origin: Position,
  receiver: Position,
  antenna: RfAntennaDraft,
): RfInputs & { directionalLossDb: number } {
  const values = [
    antenna.transmitterBearing,
    antenna.receiverBearing,
    antenna.beamwidth,
    antenna.maximumAttenuation,
  ];
  if (values.some((value) => !value.trim()))
    throw new Error('Complete the antenna pattern assumptions.');
  const inverse = Geodesic.WGS84.Inverse(origin[1], origin[0], receiver[1], receiver[0]);
  if (!inverse.s12 || inverse.s12 < 1)
    throw new Error('Separate the radio sites by at least one metre.');
  const tx = antennaAttenuation(
    inverse.azi1 ?? NaN,
    Number(antenna.transmitterBearing),
    Number(antenna.beamwidth),
    Number(antenna.maximumAttenuation),
  );
  const rx = antennaAttenuation(
    (inverse.azi2 ?? NaN) + 180,
    Number(antenna.receiverBearing),
    Number(antenna.beamwidth),
    Number(antenna.maximumAttenuation),
  );
  return { ...input, directionalLossDb: tx + rx };
}
