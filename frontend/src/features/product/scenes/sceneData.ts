/**
 * Illustrative, synthetic layer content for the story globe. Generated once from a
 * fixed seed: no live data, no real aircraft, vessels or people. Shapes echo how each
 * real layer looks (clusters, routes, orbits, interference cells) without claiming any
 * real event happened.
 */
import { LAYER_STORIES } from '../content/observe';
import {
  greatCircle,
  isLand,
  seededRandom,
  toSphere,
  type GeoPoint,
  type SpherePoint,
} from './globeMath';

export type SceneKind = 'points' | 'routes' | 'orbits' | 'cells' | 'zones';

export interface SceneLayer {
  id: string;
  kind: SceneKind;
  colour: string;
  points: SpherePoint[];
  /** For routes: each route as a sequence of points that moving markers follow. */
  routes: SpherePoint[][];
}

const HOTSPOTS = {
  conflict: [
    { lat: 48.5, lon: 37.5 },
    { lat: 31.5, lon: 34.6 },
    { lat: 15.4, lon: 32.5 },
    { lat: 13.5, lon: 2.1 },
    { lat: 21.9, lon: 96 },
    { lat: 2, lon: 45.3 },
    { lat: -1.6, lon: 29.2 },
  ],
  fires: [
    { lat: -12, lon: -55 },
    { lat: -25, lon: 133 },
    { lat: 62, lon: 105 },
    { lat: 38, lon: -121 },
    { lat: -8, lon: 22 },
    { lat: 54, lon: -118 },
  ],
  cameras: [
    { lat: 50, lon: 8 },
    { lat: 40, lon: -88 },
    { lat: 35.6, lon: 139.7 },
    { lat: 24, lon: 121 },
    { lat: 47, lon: 8.3 },
    { lat: 52, lon: 20 },
  ],
  interference: [
    { lat: 56, lon: 21 },
    { lat: 34.5, lon: 34 },
    { lat: 44, lon: 34 },
    { lat: 33, lon: 44 },
    { lat: 60, lon: 30 },
  ],
  regions: [
    { lat: 48.5, lon: 36 },
    { lat: 15, lon: 30 },
    { lat: 32, lon: 35 },
    { lat: 20, lon: 96 },
  ],
} satisfies Record<string, readonly GeoPoint[]>;

const LANES: readonly (readonly GeoPoint[])[] = [
  [
    { lat: 51.9, lon: 3.5 },
    { lat: 48.5, lon: -6 },
    { lat: 36, lon: -6.5 },
    { lat: 37, lon: 11 },
    { lat: 31.6, lon: 32.4 },
    { lat: 20, lon: 38.5 },
    { lat: 12.5, lon: 44 },
    { lat: 8, lon: 60 },
    { lat: 5.8, lon: 80.5 },
    { lat: 5.5, lon: 95 },
    { lat: 1.3, lon: 104 },
    { lat: 15, lon: 115 },
    { lat: 31, lon: 123 },
  ],
  [
    { lat: 31, lon: 124 },
    { lat: 40, lon: 160 },
    { lat: 42, lon: -160 },
    { lat: 33.5, lon: -119 },
  ],
  [
    { lat: 40.3, lon: -73.5 },
    { lat: 44, lon: -45 },
    { lat: 49, lon: -12 },
    { lat: 51, lon: 1.5 },
  ],
  [
    { lat: -34.5, lon: 18 },
    { lat: -20, lon: 2 },
    { lat: 5, lon: -10 },
    { lat: 36, lon: -9 },
  ],
];

const FLIGHTS: readonly [GeoPoint, GeoPoint][] = [
  [
    { lat: 51.5, lon: -0.5 },
    { lat: 40.6, lon: -73.8 },
  ],
  [
    { lat: 25.3, lon: 55.4 },
    { lat: 1.4, lon: 104 },
  ],
  [
    { lat: 48.4, lon: 2.6 },
    { lat: 35.8, lon: 140.4 },
  ],
  [
    { lat: 33.9, lon: -118.4 },
    { lat: -33.9, lon: 151.2 },
  ],
  [
    { lat: 52.3, lon: 13.5 },
    { lat: 25.3, lon: 55.4 },
  ],
  [
    { lat: -23.4, lon: -46.5 },
    { lat: 38.8, lon: -9.1 },
  ],
];

const CABLES: readonly [GeoPoint, GeoPoint][] = [
  [
    { lat: 50.4, lon: -4.5 },
    { lat: 40.5, lon: -73 },
  ],
  [
    { lat: 43.3, lon: 5.4 },
    { lat: 1.3, lon: 103.9 },
  ],
  [
    { lat: 35, lon: 139.8 },
    { lat: 34, lon: -120 },
  ],
  [
    { lat: -33.9, lon: 18.4 },
    { lat: 38.7, lon: -9.4 },
  ],
];

function scatter(
  random: () => number,
  centres: readonly GeoPoint[],
  each: number,
  spread: number,
  landOnly: boolean,
): GeoPoint[] {
  const points: GeoPoint[] = [];
  for (const centre of centres) {
    let placed = 0;
    for (let tries = 0; placed < each && tries < each * 12; tries += 1) {
      const lat = centre.lat + (random() - 0.5) * spread;
      const lon = centre.lon + (random() - 0.5) * spread * 1.4;
      if (landOnly && !isLand(lat, lon)) continue;
      points.push({ lat, lon });
      placed += 1;
    }
  }
  return points;
}

function anywhereOnLand(
  random: () => number,
  count: number,
  minLat = -55,
  maxLat = 70,
): GeoPoint[] {
  const points: GeoPoint[] = [];
  for (let tries = 0; points.length < count && tries < count * 40; tries += 1) {
    const lat = minLat + random() * (maxLat - minLat);
    const lon = random() * 360 - 180;
    if (isLand(lat, lon)) points.push({ lat, lon });
  }
  return points;
}

function lanes(paths: readonly (readonly GeoPoint[])[]): SpherePoint[][] {
  return paths.map((path) =>
    path
      .slice(1)
      .flatMap((point, index) =>
        greatCircle(path[index] ?? point, point, 10).slice(index === 0 ? 0 : 1),
      )
      .map(toSphere),
  );
}

function arcs(pairs: readonly [GeoPoint, GeoPoint][]): SpherePoint[][] {
  return pairs.map(([a, b]) => greatCircle(a, b, 48).map(toSphere));
}

export function buildScene(): SceneLayer[] {
  const random = seededRandom(20261007);
  const layer = (
    id: string,
    kind: SceneKind,
    points: GeoPoint[] = [],
    routes: SpherePoint[][] = [],
  ): SceneLayer => ({
    id,
    kind,
    colour: LAYER_STORIES[id]?.colour ?? '#e9e4dc',
    points: points.map(toSphere),
    routes,
  });
  return [
    layer('conflict', 'points', scatter(random, HOTSPOTS.conflict, 14, 7, true)),
    layer('disaster', 'points', [
      ...anywhereOnLand(random, 26),
      ...scatter(
        random,
        [
          { lat: 36, lon: 140 },
          { lat: -6, lon: 110 },
          { lat: -20, lon: -70 },
        ],
        6,
        10,
        false,
      ),
    ]),
    layer('fires', 'points', scatter(random, HOTSPOTS.fires, 16, 9, true)),
    layer('news', 'points', anywhereOnLand(random, 60)),
    layer('cyber', 'points', anywhereOnLand(random, 40, -40, 62)),
    layer('space', 'orbits'),
    layer('aircraft', 'routes', [], arcs(FLIGHTS)),
    layer('vessels', 'routes', [], lanes(LANES)),
    layer('cameras', 'points', scatter(random, HOTSPOTS.cameras, 12, 6, true)),
    layer('technology', 'routes', [], arcs(CABLES)),
    layer('infrastructure', 'points', anywhereOnLand(random, 34, -40, 65)),
    layer('figures', 'points', anywhereOnLand(random, 24, -40, 60)),
    layer('regions', 'zones', [...HOTSPOTS.regions]),
    layer('interference', 'cells', scatter(random, HOTSPOTS.interference, 6, 6, false)),
    layer('grid', 'cells', [
      { lat: 52.5, lon: -1.5 },
      { lat: 54.5, lon: -2.5 },
      { lat: 51.2, lon: -3.5 },
    ]),
  ];
}
