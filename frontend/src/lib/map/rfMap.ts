import { PathLayer, PolygonLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';
import type { Position } from './geoJsonTypes';
import { measurementPoint } from './measurements';
import { calculateRf } from './rfPlanning';
import type { RfInputs } from './rfPlanning';
import { RF_PHYSICAL_REFERENCE, type RfEngineeringSettings } from './rfEngineering';
import {
  rfReferenceBubble,
  rfReferenceDistance,
  rfReferenceLink,
  rfReferencePaths,
  rfReferencePoint,
  rfReferenceVisible,
} from './rfReferenceGeometry';
import type { RfReferencePath } from './rfReferenceGeometry';
import { RF_STATUS_COLOURS } from './rfTerrainPresentation';

export interface RfMapEstimate {
  origin: Position;
  receiver: Position | null;
  radiusKm: number;
  horizonKm: number;
  sensitivityDistanceKm: number;
  reserveDb?: number;
  label: string;
}

export function rfMapEstimate(
  input: RfInputs,
  origin: Position,
  receiver: Position | null = null,
  settings: RfEngineeringSettings = RF_PHYSICAL_REFERENCE,
): RfMapEstimate {
  measurementPoint(...origin);
  if (receiver) measurementPoint(...receiver);
  const result = calculateRf(input, settings);
  const radiusKm = Math.min(result.horizonKm, result.sensitivityDistanceKm);
  if (radiusKm < 0.001)
    throw new Error(
      'The estimated radius is below 1 metre. Increase antenna heights or review the link inputs.',
    );
  return {
    origin,
    receiver,
    radiusKm,
    horizonKm: result.horizonKm,
    sensitivityDistanceKm: result.sensitivityDistanceKm,
    reserveDb: settings.reserveDb,
    label: `RF estimate · ${rfReferenceDistance(radiusKm)} · no terrain model`,
  };
}

/** Fixed-size ideal reference boundary, with terrain and clutter still unchecked. */
export function rfRangeRing(estimate: RfMapEstimate): Position[] {
  return Array.from({ length: 73 }, (_, index) =>
    rfReferencePoint(estimate.origin, index * 5, estimate.radiusKm),
  );
}

interface ReferenceLabel {
  point: Position;
  label: string;
}

function referenceShade(alpha: number): [number, number, number, number] {
  const [red, green, blue] = RF_STATUS_COLOURS.clear;
  return [red, green, blue, alpha];
}

const referenceColour = ({ status }: RfReferencePath): [number, number, number, number] =>
  status === 'outside'
    ? RF_STATUS_COLOURS.blocked
    : status === 'range'
      ? referenceShade(90)
      : RF_STATUS_COLOURS.clear;

export function rfMapLayers(
  estimate: RfMapEstimate | null,
  flat: boolean,
  bubble = false,
): Layer[] {
  if (!estimate) return [];
  const ring = rfRangeRing(estimate);
  const link = rfReferenceLink(estimate);
  const visiblePaths = rfReferencePaths(
    [
      { path: ring, status: 'boundary' },
      ...(bubble
        ? [0.25, 0.5, 0.75].map((fraction): RfReferencePath => ({
            path: rfRangeRing({ ...estimate, radiusKm: estimate.radiusKm * fraction }),
            status: 'range',
          }))
        : []),
      ...link.paths,
    ],
    flat,
  );
  const points = [estimate.origin, ...(estimate.receiver ? [estimate.receiver] : [])].filter(
    (point) => rfReferenceVisible(point, flat),
  );
  const boundary = link.limit ?? rfReferencePoint(estimate.origin, 90, estimate.radiusKm);
  const boundaryReason =
    estimate.horizonKm <= estimate.sensitivityDistanceKm
      ? 'Radio horizon'
      : (estimate.reserveDb ?? 0) > 0
        ? `Sensitivity + ${estimate.reserveDb} dB reserve`
        : 'Receiver sensitivity';
  const labels: ReferenceLabel[] = [
    { point: estimate.origin, label: 'TX · 0 km\nTerrain not checked' },
    {
      point: boundary,
      label: `Ideal limit · ${rfReferenceDistance(estimate.radiusKm)}\n${boundaryReason}`,
    },
  ];
  if (estimate.receiver)
    labels.push({
      point: estimate.receiver,
      label: `RX · ${rfReferenceDistance(link.distanceKm ?? 0)}\n${link.limit ? 'Beyond ideal limit' : 'Inside ideal limit'}`,
    });
  return [
    ...(bubble
      ? [
          new PolygonLayer<Position[]>({
            id: 'rf-estimate-bubble',
            data: rfReferenceBubble(estimate, ring, flat),
            getPolygon: (polygon) => polygon,
            getFillColor: referenceShade(28),
            stroked: false,
            pickable: false,
            wrapLongitude: flat,
          }),
        ]
      : []),
    new PathLayer<RfReferencePath>({
      id: 'rf-estimate-path-underlay',
      data: visiblePaths.filter(({ status }) => status !== 'range'),
      getPath: (segment) => segment.path,
      getColor: [4, 10, 16, 230],
      getWidth: 7,
      widthUnits: 'pixels',
      pickable: false,
      wrapLongitude: flat,
    }),
    new PathLayer<RfReferencePath>({
      id: 'rf-estimate-paths',
      data: visiblePaths,
      getPath: (segment) => segment.path,
      getColor: referenceColour,
      getWidth: ({ status }) => (status === 'range' ? 1 : status === 'boundary' ? 2.5 : 4),
      widthUnits: 'pixels',
      pickable: false,
      wrapLongitude: flat,
    }),
    new ScatterplotLayer<Position>({
      id: 'rf-estimate-limit',
      data: rfReferenceVisible(boundary, flat) ? [boundary] : [],
      getPosition: (point) => point,
      getRadius: 7,
      radiusUnits: 'pixels',
      getFillColor: link.limit ? RF_STATUS_COLOURS.blocked : RF_STATUS_COLOURS.clear,
      stroked: true,
      getLineColor: [255, 255, 255, 255],
      getLineWidth: 2,
      lineWidthUnits: 'pixels',
      pickable: false,
    }),
    new ScatterplotLayer<Position>({
      id: 'rf-estimate-sites',
      data: points,
      getPosition: (point) => point,
      getRadius: 6,
      radiusUnits: 'pixels',
      getFillColor: [245, 251, 255, 255],
      stroked: true,
      getLineColor: [4, 10, 16, 255],
      getLineWidth: 2,
      lineWidthUnits: 'pixels',
      pickable: false,
    }),
    new TextLayer<ReferenceLabel>({
      id: 'rf-estimate-label',
      characterSet: 'auto',
      data: labels.filter(({ point }) => rfReferenceVisible(point, flat)),
      getPosition: (item) => item.point,
      getText: (item) => item.label,
      getSize: 12,
      getColor: [245, 251, 255, 255],
      getPixelOffset: [0, -30],
      background: true,
      backgroundPadding: [6, 4],
      getBackgroundColor: [4, 10, 16, 235],
      pickable: false,
    }),
  ];
}
