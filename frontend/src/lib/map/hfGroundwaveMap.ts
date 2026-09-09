import { PathLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import { Geodesic } from 'geographiclib-geodesic';
import type { Layer } from '@deck.gl/core';
import type { GroundwaveResult } from '@/lib/api/groundwave';
import type { RfAnalysis } from './rfAnalysis';
import type { Position } from './geoJsonTypes';
import { measure, measurementPaths, measurementPoint } from './measurements';

type GroundwaveAnalysis = Extract<RfAnalysis, { kind: 'hf-groundwave' }>;
type Sample = GroundwaveResult['samples'][number];

function validatedSamples(result: GroundwaveResult) {
  const first = result.samples[0];
  const last = result.samples[result.samples.length - 1];
  if (!first || !last || result.samples.length < 2 || result.samples.length > 64)
    throw new Error('Groundwave requires between 2 and 64 model samples.');
  let previous = 0;
  for (const sample of result.samples) {
    if (
      !Number.isFinite(sample.distance_km) ||
      sample.distance_km < 1 ||
      sample.distance_km > 200 ||
      sample.distance_km <= previous ||
      !Number.isFinite(sample.received_power_dbm)
    )
      throw new Error(
        'Groundwave samples must have finite power and increasing distances from 1 to 200 km.',
      );
    previous = sample.distance_km;
  }
  return { samples: result.samples as readonly Sample[], first, last };
}

/** Conservative first-failure contour, not a fitted coverage boundary. */
export function hfGroundwaveSummary(result: GroundwaveResult, sensitivityDbm: number) {
  if (!Number.isFinite(sensitivityDbm)) throw new Error('Receiver sensitivity must be finite.');
  const { samples, first, last } = validatedSamples(result);
  let radiusKm: number | null = null;
  let firstFailureKm: number | null = null;
  let passingSamples = 0;
  for (const sample of samples) {
    if (sample.received_power_dbm < sensitivityDbm) {
      firstFailureKm = sample.distance_km;
      break;
    }
    radiusKm = sample.distance_km;
    passingSamples++;
  }
  return {
    radiusKm,
    firstFailureKm,
    passingSamples,
    checkedFromKm: first.distance_km,
    checkedToKm: last.distance_km,
    atLimit: passingSamples === samples.length,
    noPassing: passingSamples === 0,
  };
}

/** Interpolate dBm against log distance only inside the supplied model domain. */
export function hfGroundwaveReceiver(result: GroundwaveResult, distanceKm: number) {
  const { samples, first, last } = validatedSamples(result);
  if (
    !Number.isFinite(distanceKm) ||
    distanceKm < first.distance_km ||
    distanceKm > last.distance_km
  )
    return null;
  const exact = samples.find((sample) => sample.distance_km === distanceKm);
  if (exact)
    return {
      distanceKm,
      receivedDbm: exact.received_power_dbm,
      modelOnly: true as const,
      interpolated: false,
    };
  const upperIndex = samples.findIndex((sample) => sample.distance_km > distanceKm);
  const lower = samples[upperIndex - 1];
  const upper = samples[upperIndex];
  if (!lower || !upper) return null;
  const fraction =
    Math.log(distanceKm / lower.distance_km) / Math.log(upper.distance_km / lower.distance_km);
  return {
    distanceKm,
    receivedDbm:
      lower.received_power_dbm + fraction * (upper.received_power_dbm - lower.received_power_dbm),
    modelOnly: true as const,
    interpolated: true,
  };
}

interface ColouredPath {
  path: Position[];
  colour: [number, number, number, number];
}
const CYAN: ColouredPath['colour'] = [115, 225, 240, 235];
const AMBER: ColouredPath['colour'] = [240, 181, 85, 220];
const MUTED: ColouredPath['colour'] = [120, 135, 150, 120];

function visiblePieces(path: Position[], flat: boolean): Position[][] {
  const pieces: Position[][] = [[]];
  for (const point of path) {
    if (flat && Math.abs(point[1]) > 85.05112878) pieces.push([]);
    else pieces[pieces.length - 1]?.push(point);
  }
  return pieces.filter((piece) => piece.length > 1);
}

/** Fixed ring/path budgets; no filled claim of reception or continuous animation. */
export function hfGroundwaveLayers(analysis: GroundwaveAnalysis | null, flat: boolean): Layer[] {
  if (!analysis) return [];
  measurementPoint(...analysis.origin);
  if (analysis.receiver) measurementPoint(...analysis.receiver);
  const summary = hfGroundwaveSummary(analysis.result, analysis.input.sensitivityDbm);
  const definitions = [
    { radius: summary.checkedFromKm, colour: MUTED },
    { radius: summary.radiusKm, colour: CYAN },
    { radius: summary.firstFailureKm, colour: AMBER },
  ].filter(
    (item, index, all) =>
      item.radius !== null && !all.slice(index + 1).some((later) => later.radius === item.radius),
  );
  const paths: ColouredPath[] = definitions.flatMap(({ radius, colour }) => {
    if (radius === null) return [];
    const ring = Array.from({ length: 73 }, (_, index) => {
      const point = Geodesic.WGS84.Direct(
        analysis.origin[1],
        analysis.origin[0],
        index * 5,
        radius * 1000,
      );
      return measurementPoint(point.lon2 ?? NaN, point.lat2 ?? NaN);
    });
    return visiblePieces(ring, flat).map((path) => ({ path, colour }));
  });
  const receiverEstimate = analysis.receiver
    ? hfGroundwaveReceiver(
        analysis.result,
        measure([analysis.origin, analysis.receiver], 'distance').metres / 1000,
      )
    : null;
  if (analysis.receiver && receiverEstimate) {
    const colour = receiverEstimate.receivedDbm >= analysis.input.sensitivityDbm ? CYAN : AMBER;
    for (const path of measurementPaths([analysis.origin, analysis.receiver], 'distance'))
      paths.push(...visiblePieces(path, flat).map((piece) => ({ path: piece, colour })));
  }
  const sites = [analysis.origin, ...(analysis.receiver ? [analysis.receiver] : [])].filter(
    (point) => !flat || Math.abs(point[1]) <= 85.05112878,
  );
  const caption =
    summary.radiusKm === null
      ? 'no passing range established'
      : `${summary.radiusKm.toFixed(1)} km last passing sample${summary.atLimit ? ' (search limit)' : ''}`;
  return [
    new PathLayer<ColouredPath>({
      id: 'hf-groundwave-reference-rings',
      data: paths,
      getPath: (item) => item.path,
      getColor: (item) => item.colour,
      getWidth: 2,
      widthUnits: 'pixels',
      pickable: false,
      wrapLongitude: flat,
    }),
    new ScatterplotLayer<Position>({
      id: 'hf-groundwave-sites',
      data: sites,
      getPosition: (point) => point,
      getRadius: 6,
      radiusUnits: 'pixels',
      getFillColor: CYAN,
      pickable: false,
    }),
    new TextLayer<Position>({
      id: 'hf-groundwave-label',
      data: sites.filter((point) => point === analysis.origin),
      getPosition: (point) => point,
      getText: () => `HF groundwave · ${caption}\nHomogeneous ground scenario · no terrain`,
      getSize: 12,
      getColor: [220, 230, 235, 255],
      getPixelOffset: [0, -24],
      background: true,
      getBackgroundColor: [8, 12, 16, 225],
      pickable: false,
    }),
  ];
}
