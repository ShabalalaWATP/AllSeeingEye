import { Geodesic } from 'geographiclib-geodesic';
import { PathLayer, PolygonLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';
import type { Position } from './geoJsonTypes';
import type { RfTerrainAnalysis, RfTerrainStatus } from './rfTerrainTypes';

interface Segment {
  path: Position[];
  status: RfTerrainStatus;
}
const colours: Record<RfTerrainStatus, [number, number, number, number]> = {
  clear: [99, 225, 235, 235],
  risk: [250, 187, 76, 235],
  blocked: [250, 142, 76, 235],
  unknown: [155, 161, 174, 200],
};
function direct(origin: Position, bearing: number, distanceKm: number): Position {
  const point = Geodesic.WGS84.Direct(origin[1], origin[0], bearing, distanceKm * 1000);
  return [point.lon2 ?? origin[0], point.lat2 ?? origin[1]];
}
function continuous(ring: Position[]): Position[] {
  return ring.reduce<Position[]>((points, [lon, lat]) => {
    const previous = points.at(-1);
    points.push([
      previous ? previous[0] + (((((lon - previous[0] + 180) % 360) + 360) % 360) - 180) : lon,
      lat,
    ]);
    return points;
  }, []);
}
function clipPaths(segments: Segment[], flat: boolean): Segment[] {
  return segments.flatMap(({ path, status }) => {
    const pieces: Position[][] = [[]];
    for (const point of path) {
      if (flat && Math.abs(point[1]) > 85.05112878) pieces.push([]);
      else pieces.at(-1)?.push(point);
    }
    return pieces.filter((piece) => piece.length > 1).map((piece) => ({ path: piece, status }));
  });
}

/** Static sample marks and narrow wedges, deliberately leaving unsampled azimuths empty. */
export function rfTerrainLayers(analysis: RfTerrainAnalysis | null, flat: boolean): Layer[] {
  if (!analysis) return [];
  const segments: Segment[] = [];
  const wedges: Position[][] = [];
  const samples: { point: Position; status: RfTerrainStatus }[] = [];
  if (analysis.path) {
    for (const [index, point] of analysis.path.points.entries()) {
      const previous = analysis.path.points[index - 1];
      const status: RfTerrainStatus =
        analysis.path.status === 'unknown' || point.clearanceM === null
          ? 'unknown'
          : point.clearanceM <= 0
            ? 'blocked'
            : (point.fresnelClearanceM ?? 0) < 0 || (analysis.path.marginDb ?? -Infinity) < 0
              ? 'risk'
              : 'clear';
      samples.push({ point: point.position, status });
      if (previous) segments.push({ path: [previous.position, point.position], status });
    }
  }
  for (const radial of analysis.radials) {
    let previous = analysis.origin;
    for (const sample of radial.samples) {
      segments.push({ path: [previous, sample.position], status: sample.status });
      samples.push({ point: sample.position, status: sample.status });
      previous = sample.position;
    }
    if (radial.clearDistanceKm > 0)
      wedges.push(
        continuous([
          analysis.origin,
          direct(analysis.origin, radial.bearingDegrees - 1.5, radial.clearDistanceKm),
          direct(analysis.origin, radial.bearingDegrees + 1.5, radial.clearDistanceKm),
        ]),
      );
  }
  const rangeRings =
    analysis.kind === 'radial'
      ? [0.25, 0.5, 0.75, 1].map((fraction) =>
          Array.from({ length: 73 }, (_, index) =>
            direct(analysis.origin, index * 5, analysis.maxDistanceKm * fraction),
          ),
        )
      : [];
  const sites = [
    { point: analysis.origin, label: 'TX' },
    ...(analysis.receiver ? [{ point: analysis.receiver, label: 'RX' }] : []),
  ].filter(({ point }) => !flat || Math.abs(point[1]) <= 85.05112878);
  const labels = [
    ...sites.map((site) => ({ ...site, label: `${site.label} · sampled terrain screen` })),
    ...(analysis.kind === 'radial'
      ? [0.25, 0.5, 0.75, 1].map((fraction) => ({
          point: direct(analysis.origin, 90, analysis.maxDistanceKm * fraction),
          label: `${(analysis.maxDistanceKm * fraction).toFixed(1)} km`,
        }))
      : []),
  ].filter(({ point }) => !flat || Math.abs(point[1]) <= 85.05112878);
  return [
    new PolygonLayer<Position[]>({
      id: 'rf-terrain-sampled-sectors',
      data: wedges.filter(
        (ring) => !flat || ring.every((point) => Math.abs(point[1]) <= 85.05112878),
      ),
      getPolygon: (ring) => ring,
      getFillColor: [99, 225, 235, 28],
      stroked: false,
      pickable: false,
      wrapLongitude: flat,
    }),
    new PathLayer<Segment>({
      id: 'rf-terrain-range-rings',
      data: clipPaths(
        rangeRings.map((path) => ({ path, status: 'unknown' })),
        flat,
      ),
      getPath: (item) => item.path,
      getColor: [150, 170, 190, 70],
      getWidth: 1,
      widthUnits: 'pixels',
      pickable: false,
      wrapLongitude: flat,
    }),
    new PathLayer<Segment>({
      id: 'rf-terrain-paths',
      data: clipPaths(segments, flat),
      getPath: (item) => item.path,
      getColor: (item) => colours[item.status],
      getWidth: 2,
      widthUnits: 'pixels',
      pickable: false,
      wrapLongitude: flat,
    }),
    new ScatterplotLayer<(typeof samples)[number]>({
      id: 'rf-terrain-samples',
      data: samples.filter(({ point }) => !flat || Math.abs(point[1]) <= 85.05112878),
      getPosition: (item) => item.point,
      getFillColor: (item) => colours[item.status],
      getRadius: 3,
      radiusUnits: 'pixels',
      pickable: false,
    }),
    new ScatterplotLayer<(typeof sites)[number]>({
      id: 'rf-terrain-sites',
      data: sites,
      getPosition: (item) => item.point,
      getFillColor: [230, 250, 255, 255],
      getRadius: 6,
      radiusUnits: 'pixels',
      pickable: false,
    }),
    new TextLayer<(typeof labels)[number]>({
      id: 'rf-terrain-labels',
      data: labels,
      getPosition: (item) => item.point,
      getText: (item) => item.label,
      getSize: 11,
      getColor: [220, 240, 250, 255],
      getPixelOffset: [0, -20],
      background: true,
      getBackgroundColor: [8, 12, 18, 225],
      pickable: false,
    }),
  ];
}
