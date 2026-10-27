/**
 * Builds the synthetic scene behind the product page's story globe and writes it to
 * src/features/product/scenes/sceneData.generated.json. Every point comes from a fixed
 * seed scattered around broad regions, rounded to two decimal places, so the file holds
 * no real event, track, aircraft, vessel or person. Route layers keep only the fixed
 * waypoints the page interpolates; satellites are drawn from orbital parameters in the
 * page itself. Re-run after changing the land mask or the regions below:
 *
 *     node scripts/product-scene.js
 *
 * sceneData.unit.test.ts regenerates the scene and fails if the committed file differs.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const SCENE_SEED = 20261007;
const COLUMNS = 360;
const ROWS = 180;
const SCENES = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../src/features/product/scenes',
);
const MASK_SOURCE = path.join(SCENES, 'landMask.generated.ts');
const OUTPUT = path.join(SCENES, 'sceneData.generated.json');

const HOTSPOTS = {
  conflict: [
    [48.5, 37.5],
    [31.5, 34.6],
    [15.4, 32.5],
    [13.5, 2.1],
    [21.9, 96],
    [2, 45.3],
    [-1.6, 29.2],
  ],
  hazards: [
    [36, 140],
    [-6, 110],
    [-20, -70],
  ],
  fires: [
    [-12, -55],
    [-25, 133],
    [62, 105],
    [38, -121],
    [-8, 22],
    [54, -118],
  ],
  cameras: [
    [50, 8],
    [40, -88],
    [35.6, 139.7],
    [24, 121],
    [47, 8.3],
    [52, 20],
  ],
  interference: [
    [56, 21],
    [34.5, 34],
    [44, 34],
    [33, 44],
    [60, 30],
  ],
};

const REGIONS = [
  [48.5, 36],
  [15, 30],
  [32, 35],
  [20, 96],
];
const GRID = [
  [52.5, -1.5],
  [54.5, -2.5],
  [51.2, -3.5],
];

/** Broad shipping lanes, interpolated ten steps per leg. */
const LANES = [
  [
    [51.9, 3.5],
    [48.5, -6],
    [36, -6.5],
    [37, 11],
    [31.6, 32.4],
    [20, 38.5],
    [12.5, 44],
    [8, 60],
    [5.8, 80.5],
    [5.5, 95],
    [1.3, 104],
    [15, 115],
    [31, 123],
  ],
  [
    [31, 124],
    [40, 160],
    [42, -160],
    [33.5, -119],
  ],
  [
    [40.3, -73.5],
    [44, -45],
    [49, -12],
    [51, 1.5],
  ],
  [
    [-34.5, 18],
    [-20, 2],
    [5, -10],
    [36, -9],
  ],
];
/** City-pair arcs between major hubs, not real flights. */
const FLIGHTS = [
  [
    [51.5, -0.5],
    [40.6, -73.8],
  ],
  [
    [25.3, 55.4],
    [1.4, 104],
  ],
  [
    [48.4, 2.6],
    [35.8, 140.4],
  ],
  [
    [33.9, -118.4],
    [-33.9, 151.2],
  ],
  [
    [52.3, 13.5],
    [25.3, 55.4],
  ],
  [
    [-23.4, -46.5],
    [38.8, -9.1],
  ],
];
/** Schematic cable landings, not a survey of real systems. */
const CABLES = [
  [
    [50.4, -4.5],
    [40.5, -73],
  ],
  [
    [43.3, 5.4],
    [1.3, 103.9],
  ],
  [
    [35, 139.8],
    [34, -120],
  ],
  [
    [-33.9, 18.4],
    [38.7, -9.4],
  ],
];

/** The same small generator the page used before the scene was committed. */
export function seededRandom(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function landTest(maskBase64) {
  const bytes = Buffer.from(maskBase64, 'base64');
  return (lat, lon) => {
    const row = Math.min(ROWS - 1, Math.max(0, Math.floor(90 - lat)));
    const wrapped = (((lon + 180) % 360) + 360) % 360;
    const column = Math.min(COLUMNS - 1, Math.floor(wrapped));
    const index = row * COLUMNS + column;
    return (((bytes[index >> 3] ?? 0) >> (index & 7)) & 1) === 1;
  };
}

const round = (value) => Math.round(value * 100) / 100;
const point = (lat, lon) => [round(lat), round(lon)];

/** Builds the scene. Pure: the same land mask always gives the same scene. */
export function buildProductScene(maskBase64) {
  const random = seededRandom(SCENE_SEED);
  const isLand = landTest(maskBase64);
  const scatter = (centres, each, spread, landOnly) => {
    const points = [];
    for (const [cLat, cLon] of centres) {
      let placed = 0;
      for (let tries = 0; placed < each && tries < each * 12; tries += 1) {
        const lat = cLat + (random() - 0.5) * spread;
        const lon = cLon + (random() - 0.5) * spread * 1.4;
        if (landOnly && !isLand(lat, lon)) continue;
        points.push(point(lat, lon));
        placed += 1;
      }
    }
    return points;
  };
  const anywhereOnLand = (count, minLat = -55, maxLat = 70) => {
    const points = [];
    for (let tries = 0; points.length < count && tries < count * 40; tries += 1) {
      const lat = minLat + random() * (maxLat - minLat);
      const lon = random() * 360 - 180;
      if (isLand(lat, lon)) points.push(point(lat, lon));
    }
    return points;
  };
  const points = (id, kind, list) => ({ id, kind, points: list, routes: [], steps: 0 });
  const routes = (id, list, steps) => ({ id, kind: 'routes', points: [], routes: list, steps });
  // The draw order matters: it consumes the seeded sequence in a fixed order.
  return {
    seed: SCENE_SEED,
    layers: [
      points('conflict', 'points', scatter(HOTSPOTS.conflict, 14, 7, true)),
      points('disaster', 'points', [
        ...anywhereOnLand(26),
        ...scatter(HOTSPOTS.hazards, 6, 10, false),
      ]),
      points('fires', 'points', scatter(HOTSPOTS.fires, 16, 9, true)),
      points('news', 'points', anywhereOnLand(60)),
      points('cyber', 'points', anywhereOnLand(40, -40, 62)),
      points('space', 'orbits', []),
      routes('aircraft', FLIGHTS, 48),
      routes('vessels', LANES, 10),
      points('cameras', 'points', scatter(HOTSPOTS.cameras, 12, 6, true)),
      routes('technology', CABLES, 48),
      points('infrastructure', 'points', anywhereOnLand(34, -40, 65)),
      points('figures', 'points', anywhereOnLand(24, -40, 60)),
      points('regions', 'zones', REGIONS),
      points('interference', 'cells', scatter(HOTSPOTS.interference, 6, 6, false)),
      points('grid', 'cells', GRID),
    ],
  };
}

/** One coordinate pair per line, laid out the way Prettier formats JSON. */
export function serialiseScene(scene) {
  const pairs = (list, indent) =>
    list.length === 0
      ? '[]'
      : `[\n${list.map((pair) => `${indent}  [${pair.join(', ')}]`).join(',\n')}\n${indent}]`;
  const layer = (entry) =>
    [
      '    {',
      `      "id": ${JSON.stringify(entry.id)},`,
      `      "kind": ${JSON.stringify(entry.kind)},`,
      `      "points": ${pairs(entry.points, '      ')},`,
      `      "routes": ${
        entry.routes.length === 0
          ? '[]'
          : `[\n${entry.routes.map((route) => `        ${pairs(route, '        ')}`).join(',\n')}\n      ]`
      },`,
      `      "steps": ${entry.steps}`,
      '    }',
    ].join('\n');
  return `{\n  "seed": ${scene.seed},\n  "layers": [\n${scene.layers.map(layer).join(',\n')}\n  ]\n}\n`;
}

export function readLandMask(source = readFileSync(MASK_SOURCE, 'utf8')) {
  const parts = [...source.matchAll(/'([A-Za-z0-9+/=]*)'/g)].map((match) => match[1]);
  if (parts.length === 0) throw new Error('No land mask found.');
  return parts.join('');
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const scene = buildProductScene(readLandMask());
  writeFileSync(OUTPUT, serialiseScene(scene));
  const total = scene.layers.reduce((sum, entry) => sum + entry.points.length, 0);
  console.log(`Wrote ${path.relative(process.cwd(), OUTPUT)} with ${total} synthetic points.`);
}
