/**
 * Illustrative, synthetic layer content for the story globe, read from the committed
 * sceneData.generated.json (written by frontend/scripts/product-scene.js from a fixed
 * seed): no live data, no real aircraft, vessels or people. Shapes echo how each real
 * layer looks (clusters, routes, orbits, interference cells) without claiming any real
 * event happened. Routes are stored as waypoints and interpolated here.
 */
import { LAYER_STORIES } from '../content/observe';
import { greatCircle, toSphere, type GeoPoint, type SpherePoint } from './globeMath';
import generated from './sceneData.generated.json';

export type SceneKind = 'points' | 'routes' | 'orbits' | 'cells' | 'zones';

export interface SceneLayer {
  id: string;
  kind: SceneKind;
  colour: string;
  points: SpherePoint[];
  /** For routes: each route as a sequence of points that moving markers follow. */
  routes: SpherePoint[][];
}

interface GeneratedLayer {
  id: string;
  kind: string;
  points: number[][];
  routes: number[][][];
  steps: number;
}

/** Satellites ride these rings; the Space layer has no stored points. */
export const ORBITS = [
  { tilt: 52, phase: 0, speed: 0.11, count: 7 },
  { tilt: 98, phase: 1.3, speed: 0.08, count: 6 },
  { tilt: 28, phase: 2.6, speed: 0.06, count: 5 },
] as const;

const KINDS: readonly SceneKind[] = ['points', 'routes', 'orbits', 'cells', 'zones'];

function geo(pair: readonly number[]): GeoPoint {
  return { lat: pair[0] ?? 0, lon: pair[1] ?? 0 };
}

function interpolate(waypoints: readonly number[][], steps: number): SpherePoint[] {
  const path = waypoints.map(geo);
  return path
    .slice(1)
    .flatMap((point, index) =>
      greatCircle(path[index] ?? point, point, steps).slice(index === 0 ? 0 : 1),
    )
    .map(toSphere);
}

function kindOf(kind: string): SceneKind {
  const known = KINDS.find((entry) => entry === kind);
  if (known === undefined) throw new Error(`Unknown scene layer kind: ${kind}`);
  return known;
}

/** The generated layers exactly as committed, for counts and the determinism test. */
export const GENERATED_LAYERS: readonly GeneratedLayer[] = generated.layers;

export function buildScene(): SceneLayer[] {
  return GENERATED_LAYERS.map((layer) => ({
    id: layer.id,
    kind: kindOf(layer.kind),
    colour: LAYER_STORIES[layer.id]?.colour ?? '#e9e4dc',
    points: layer.points.map((pair) => toSphere(geo(pair))),
    routes: layer.routes.map((route) => interpolate(route, layer.steps)),
  }));
}

/** What each layer draws on the illustrative globe: points, routes or satellites. */
export function sceneCount(layer: GeneratedLayer): number {
  if (layer.kind === 'orbits') return ORBITS.reduce((sum, orbit) => sum + orbit.count, 0);
  return layer.kind === 'routes' ? layer.routes.length : layer.points.length;
}

const NOUNS: Record<SceneKind, string> = {
  points: 'points',
  routes: 'routes',
  orbits: 'satellites',
  cells: 'cells',
  zones: 'zones',
};

export interface SceneCount {
  value: number;
  noun: string;
}

/** Illustrative counts per layer id, derived from the committed synthetic scene. */
export const SCENE_COUNTS: Readonly<Record<string, SceneCount>> = Object.fromEntries(
  GENERATED_LAYERS.map((layer) => [
    layer.id,
    { value: sceneCount(layer), noun: NOUNS[kindOf(layer.kind)] },
  ]),
);
