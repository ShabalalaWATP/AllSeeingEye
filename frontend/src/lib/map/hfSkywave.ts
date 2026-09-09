/**
 * Educational single-hop virtual-shell geometry, not ITU-R P.533 or a forecast.
 * Hop geometry: Australian Bureau of Meteorology, Introduction to HF Radio Propagation.
 * Local secant-law approximation: NBS Circular 462, Ionospheric Radio Propagation.
 * https://www.sws.bom.gov.au/Educational/5/2/2
 * https://nvlpubs.nist.gov/nistpubs/Legacy/circ/nbscircular462.pdf
 */
const EARTH_KM = 6371;
const DEG = Math.PI / 180;

export interface HfSkywaveInputs {
  frequencyMHz: number;
  /** User-supplied vertical critical frequency, not a live observation. */
  criticalFrequencyMHz: number;
  virtualHeightKm: number;
  minElevationDeg: number;
  maxElevationDeg: number;
}

export interface HfSkywaveResult {
  compatible: boolean;
  innerRadiusKm: number | null;
  outerRadiusKm: number | null;
  /** Basic secant-law gate at the lowest assumed launch angle, not a predicted MUF. */
  maxFrequencyMHz: number;
  minElevationDeg: number;
  maxElevationDeg: number;
  virtualHeightKm: number;
  assumptions: string;
}

export const HF_SKYWAVE_ASSUMPTIONS =
  'User-defined, uniform virtual ionospheric shell and approximate secant-law gate. Single hop only. ' +
  'No live ionosphere, absorption, signal level, antenna pattern, magnetic effects or reliability prediction. ' +
  'The annulus is a geometric scenario, not a coverage footprint.';

function bounded(value: number, min: number, max: number, name: string) {
  if (!Number.isFinite(value) || value < min || value > max)
    throw new Error(`${name}: enter a value from ${min} to ${max}.`);
}

/** A straight virtual ray intersects a concentric shell, then returns symmetrically. */
export function hfVirtualHop(virtualHeightKm: number, elevationDeg: number) {
  bounded(virtualHeightKm, 80, 600, 'Virtual layer height (km)');
  bounded(elevationDeg, 0, 90, 'Launch elevation (degrees)');
  const angle = elevationDeg * DEG;
  const radius = EARTH_KM + virtualHeightKm;
  const radial = EARTH_KM * Math.sin(angle);
  const halfPathKm =
    Math.sqrt(radial ** 2 + 2 * EARTH_KM * virtualHeightKm + virtualHeightKm ** 2) - radial;
  const theta = Math.atan2(halfPathKm * Math.cos(angle), EARTH_KM + halfPathKm * Math.sin(angle));
  const incidenceCosine = (radial + halfPathKm) / radius;
  return {
    groundDistanceKm: elevationDeg === 90 ? 0 : 2 * EARTH_KM * theta,
    virtualPathKm: 2 * halfPathKm,
    secantFactor: 1 / incidenceCosine,
  };
}

export function calculateHfSkywave(input: HfSkywaveInputs): HfSkywaveResult {
  bounded(input.frequencyMHz, 1.6, 30, 'HF frequency (MHz)');
  bounded(input.criticalFrequencyMHz, 0.5, 20, 'Assumed critical frequency (MHz)');
  bounded(input.virtualHeightKm, 80, 600, 'Virtual layer height (km)');
  bounded(input.minElevationDeg, 0, 90, 'Minimum launch elevation (degrees)');
  bounded(input.maxElevationDeg, input.minElevationDeg, 90, 'Maximum launch elevation (degrees)');
  const farthest = hfVirtualHop(input.virtualHeightKm, input.minElevationDeg);
  const maxFrequencyMHz = input.criticalFrequencyMHz * farthest.secantFactor;
  const base = {
    maxFrequencyMHz,
    minElevationDeg: input.minElevationDeg,
    maxElevationDeg: input.maxElevationDeg,
    virtualHeightKm: input.virtualHeightKm,
    assumptions: HF_SKYWAVE_ASSUMPTIONS,
  };
  if (input.frequencyMHz > maxFrequencyMHz + 1e-10)
    return { ...base, compatible: false, innerRadiusKm: null, outerRadiusKm: null };
  // Solve the local secant-law gate for the highest admissible launch elevation.
  // This simplified shell is deliberately not presented as an ionospheric ray tracer.
  const cosineLimit =
    input.frequencyMHz <= input.criticalFrequencyMHz
      ? 0
      : ((EARTH_KM + input.virtualHeightKm) / EARTH_KM) *
        Math.sqrt(1 - (input.criticalFrequencyMHz / input.frequencyMHz) ** 2);
  const maximum = Math.min(input.maxElevationDeg, Math.acos(Math.min(1, cosineLimit)) / DEG);
  return {
    ...base,
    maxElevationDeg: maximum,
    compatible: true,
    innerRadiusKm: hfVirtualHop(input.virtualHeightKm, maximum).groundDistanceKm,
    outerRadiusKm: farthest.groundDistanceKm,
  };
}
