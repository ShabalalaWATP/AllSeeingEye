import { PathLayer, PolygonLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';
import type { Position } from './geoJsonTypes';
import type { RfTerrainAnalysis, RfTerrainStatus } from './rfTerrainTypes';
import {
  RF_STATUS_COLOURS,
  rfContinuousRing,
  rfDestination,
  rfInterpolatedFootprint,
  rfPathPointStatus,
  rfPathSegmentStatus,
  rfPathSummary,
} from './rfTerrainPresentation';

interface Segment {
  path: Position[];
  status: RfTerrainStatus;
}
interface Mark {
  point: Position;
  status: RfTerrainStatus;
}
interface Label extends Mark {
  label: string;
}
const visible = (point: Position, flat: boolean) => !flat || Math.abs(point[1]) <= 85.05112878;
const km = (distance: number) => `${distance.toFixed(distance < 1 ? 2 : 1)} km`;

function clipPaths(segments: Segment[], flat: boolean): Segment[] {
  return segments.flatMap(({ path, status }) => {
    const pieces: Position[][] = [[]];
    for (const point of path) {
      if (!visible(point, flat)) pieces.push([]);
      else pieces.at(-1)?.push(point);
    }
    return pieces.filter((piece) => piece.length > 1).map((piece) => ({ path: piece, status }));
  });
}

/** Static, bounded geometry. Filled interpolation never replaces the actual sampled rays. */
export function rfTerrainLayers(
  analysis: RfTerrainAnalysis | null,
  flat: boolean,
  bubble = false,
): Layer[] {
  if (!analysis) return [];
  const segments: Segment[] = [],
    unassessed: Segment[] = [];
  const wedges: Position[][] = [];
  const samples: Mark[] = [],
    stops: Mark[] = [];
  const labels: Label[] = [];
  if (analysis.path) {
    const profile = analysis.path,
      summary = rfPathSummary(profile);
    for (const [index, point] of profile.points.entries()) {
      const previous = profile.points[index - 1];
      samples.push({ point: point.position, status: rfPathPointStatus(profile, point, summary) });
      if (previous)
        segments.push({
          path: [previous.position, point.position],
          status: rfPathSegmentStatus(profile, previous, point, summary),
        });
    }
    const obstruction = summary.firstBlocked ?? summary.firstRisk;
    if (obstruction) {
      const status = summary.firstBlocked ? 'blocked' : 'risk';
      stops.push({ point: obstruction.position, status });
      labels.push({
        point: obstruction.position,
        status,
        label: summary.firstBlocked
          ? `First sampled obstruction · ${km(obstruction.distanceM / 1000)}\nDirect ray remains obstructed beyond this point`
          : `First sampled Fresnel intrusion · ${km(obstruction.distanceM / 1000)}`,
      });
    }
  }
  const ranked = [...analysis.radials].sort((a, b) => a.clearDistanceKm - b.clearDistanceKm);
  // Up to three informative callouts avoid 24 overlapping paragraphs around the transmitter.
  const firstFailed = analysis.radials.find((r) => r.status !== 'clear');
  const labelled = new Set(firstFailed ? [ranked[0], ranked.at(-1), firstFailed] : []);
  for (const radial of analysis.radials) {
    let previous = analysis.origin;
    for (const sample of radial.samples) {
      segments.push({ path: [previous, sample.position], status: sample.status });
      samples.push({ point: sample.position, status: sample.status });
      previous = sample.position;
    }
    if (radial.clearDistanceKm > 0)
      wedges.push(
        rfContinuousRing([
          analysis.origin,
          rfDestination(analysis.origin, radial.bearingDegrees - 1.5, radial.clearDistanceKm),
          rfDestination(analysis.origin, radial.bearingDegrees + 1.5, radial.clearDistanceKm),
        ]),
      );
    const last = radial.samples.at(-1);
    if (!last) continue;
    const stopDistanceKm = radial.stopDistanceKm;
    if (stopDistanceKm !== null) {
      stops.push({ point: last.position, status: last.status });
      const remaining = analysis.maxDistanceKm - stopDistanceKm;
      // Sparse grey marks represent an unassessed tail, never simulated reception recovery.
      for (let step = 0; step < 4 && remaining > 0; step++)
        unassessed.push({
          path: [0.15, 0.65].map((offset) =>
            rfDestination(
              analysis.origin,
              radial.bearingDegrees,
              stopDistanceKm + ((step + offset) * remaining) / 4,
            ),
          ),
          status: 'unknown',
        });
    }
    if (labelled.has(radial))
      labels.push({
        point: last.position,
        status: radial.status,
        label:
          radial.stopDistanceKm === null
            ? `${radial.bearingDegrees.toFixed(0)}° · passes to survey limit ${km(radial.clearDistanceKm)}`
            : `${radial.bearingDegrees.toFixed(0)}° · first ${radial.status === 'unknown' ? 'unknown' : 'failing'} target ${km(last.distanceKm)}\n${radial.clearDistanceKm > 0 ? `Last pass ${km(radial.clearDistanceKm)}` : 'No passing target established'} · beyond stop unassessed`,
      });
  }
  const rings =
    analysis.kind === 'radial'
      ? [0.25, 0.5, 0.75, 1].map((fraction) =>
          Array.from({ length: 73 }, (_, index) =>
            rfDestination(analysis.origin, index * 5, analysis.maxDistanceKm * fraction),
          ),
        )
      : [];
  const sites: Label[] = [
    { point: analysis.origin, label: 'TX · transmitter', status: 'clear' },
    ...(analysis.receiver
      ? [
          {
            point: analysis.receiver,
            label: `RX · ${km(analysis.maxDistanceKm)} · ${analysis.path?.status === 'blocked' ? 'direct ray obstructed' : analysis.path?.status === 'unknown' ? 'terrain unknown' : analysis.path?.status === 'risk' ? 'link at risk' : 'sampled screen passes'}`,
            status: analysis.path?.status ?? 'unknown',
          } satisfies Label,
        ]
      : []),
  ];
  labels.push(...sites);
  if (analysis.kind === 'radial')
    labels.push({
      point: rfDestination(analysis.origin, 90, analysis.maxDistanceKm),
      status: 'unknown',
      label: `Survey limit · ${km(analysis.maxDistanceKm)}\nNot a maximum reception range`,
    });
  const footprint = bubble ? rfInterpolatedFootprint(analysis) : [];
  if (footprint.length)
    labels.push({
      point: rfDestination(analysis.origin, 180, analysis.maxDistanceKm * 0.35),
      status: 'clear',
      label: 'Interpolated estimate\nBetween bearings is not terrain-verified',
    });
  const paths = clipPaths(segments, flat);
  const layerOptions = { pickable: false, wrapLongitude: flat };
  return [
    new PolygonLayer<Position[]>({
      id: 'rf-terrain-interpolated-footprint',
      data: footprint.filter((ring) => ring.every((point) => visible(point, flat))),
      getPolygon: (ring) => ring,
      getFillColor: [45, 235, 195, 22],
      getLineColor: [45, 235, 195, 100],
      getLineWidth: 1,
      lineWidthUnits: 'pixels',
      stroked: true,
      ...layerOptions,
    }),
    new PolygonLayer<Position[]>({
      id: 'rf-terrain-sampled-sectors',
      data: wedges.filter((ring) => ring.every((point) => visible(point, flat))),
      getPolygon: (ring) => ring,
      getFillColor: [45, 235, 195, 42],
      stroked: false,
      ...layerOptions,
    }),
    new PathLayer<Segment>({
      id: 'rf-terrain-range-rings',
      data: clipPaths(
        rings.map((path) => ({ path, status: 'unknown' })),
        flat,
      ),
      getPath: (item) => item.path,
      getColor: [154, 167, 188, 115],
      getWidth: 1,
      widthUnits: 'pixels',
      ...layerOptions,
    }),
    new PathLayer<Segment>({
      id: 'rf-terrain-unassessed',
      data: clipPaths(unassessed, flat),
      getPath: (item) => item.path,
      getColor: RF_STATUS_COLOURS.unknown,
      getWidth: 1.5,
      widthUnits: 'pixels',
      ...layerOptions,
    }),
    new PathLayer<Segment>({
      id: 'rf-terrain-path-underlay',
      data: paths,
      getPath: (item) => item.path,
      getColor: [2, 7, 12, 240],
      getWidth: 7,
      widthUnits: 'pixels',
      ...layerOptions,
    }),
    new PathLayer<Segment>({
      id: 'rf-terrain-paths',
      data: paths,
      getPath: (item) => item.path,
      getColor: (item) => RF_STATUS_COLOURS[item.status],
      getWidth: 3.5,
      widthUnits: 'pixels',
      ...layerOptions,
    }),
    new ScatterplotLayer<Mark>({
      id: 'rf-terrain-samples',
      data: samples.filter(({ point }) => visible(point, flat)),
      getPosition: (item) => item.point,
      getFillColor: (item) => RF_STATUS_COLOURS[item.status],
      getRadius: 3,
      radiusUnits: 'pixels',
      pickable: false,
    }),
    new ScatterplotLayer<Mark>({
      id: 'rf-terrain-stops',
      data: stops.filter(({ point }) => visible(point, flat)),
      getPosition: (item) => item.point,
      getFillColor: [2, 7, 12, 255],
      getLineColor: (item) => RF_STATUS_COLOURS[item.status],
      getLineWidth: 2,
      lineWidthUnits: 'pixels',
      stroked: true,
      getRadius: 8,
      radiusUnits: 'pixels',
      pickable: false,
    }),
    new TextLayer<Mark>({
      id: 'rf-terrain-stop-symbols',
      data: stops.filter(({ point }) => visible(point, flat)),
      getPosition: (item) => item.point,
      getText: (item) => (item.status === 'unknown' ? '?' : item.status === 'risk' ? '△' : '×'),
      getSize: 15,
      getColor: (item) => RF_STATUS_COLOURS[item.status],
      pickable: false,
    }),
    new ScatterplotLayer<Label>({
      id: 'rf-terrain-sites',
      data: sites.filter(({ point }) => visible(point, flat)),
      getPosition: (item) => item.point,
      getFillColor: [240, 250, 255, 255],
      getLineColor: [2, 7, 12, 255],
      stroked: true,
      getLineWidth: 2,
      lineWidthUnits: 'pixels',
      getRadius: 6,
      radiusUnits: 'pixels',
      pickable: false,
    }),
    new TextLayer<Label>({
      id: 'rf-terrain-labels',
      data: labels.filter(({ point }) => visible(point, flat)),
      getPosition: (item) => item.point,
      getText: (item) => item.label,
      getSize: 11,
      getColor: (item) => RF_STATUS_COLOURS[item.status],
      getPixelOffset: [0, -25],
      background: true,
      getBackgroundColor: [2, 7, 12, 240],
      backgroundPadding: [6, 4],
      pickable: false,
    }),
  ];
}
