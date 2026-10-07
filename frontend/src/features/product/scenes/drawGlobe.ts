/**
 * Draws one frame of the story globe on a 2D canvas: atmosphere, ocean, land dots
 * shaded towards the limb, then each revealed layer in its map colour. Only
 * transforms, alpha and simple shapes; no allocation-heavy work per frame beyond
 * projecting the visible points.
 */
import { project, toSphere, type SpherePoint, type View } from './globeMath';
import type { SceneLayer } from './sceneData';

export interface FrameState {
  view: View;
  /** Layers revealed so far; fractional values fade the newest layer in. */
  revealed: number;
  /** Seconds since the scene started, for pulses and moving markers. */
  time: number;
  /** Index of the layer the text is currently describing, emphasised on the globe. */
  active: number;
}

const ORBITS = [
  { tilt: 52, phase: 0, speed: 0.11, count: 7 },
  { tilt: 98, phase: 1.3, speed: 0.08, count: 6 },
  { tilt: 28, phase: 2.6, speed: 0.06, count: 5 },
];

function withAlpha(hex: string, alpha: number): string {
  const value = Math.round(Math.min(1, Math.max(0, alpha)) * 255)
    .toString(16)
    .padStart(2, '0');
  return `${hex}${value}`;
}

function drawBase(ctx: CanvasRenderingContext2D, view: View): void {
  const { cx, cy, radius } = view;
  const glow = ctx.createRadialGradient(cx, cy, radius * 0.9, cx, cy, radius * 1.35);
  glow.addColorStop(0, 'rgba(255,111,55,0.22)');
  glow.addColorStop(0.35, 'rgba(255,111,55,0.06)');
  glow.addColorStop(1, 'rgba(255,111,55,0)');
  ctx.fillStyle = glow;
  ctx.beginPath();
  ctx.arc(cx, cy, radius * 1.35, 0, Math.PI * 2);
  ctx.fill();
  const ocean = ctx.createRadialGradient(
    cx - radius * 0.35,
    cy - radius * 0.4,
    radius * 0.1,
    cx,
    cy,
    radius,
  );
  ocean.addColorStop(0, '#1a1622');
  ocean.addColorStop(1, '#09080d');
  ctx.fillStyle = ocean;
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = 'rgba(255,111,55,0.35)';
  ctx.lineWidth = 1;
  ctx.stroke();
}

/** Reused between frames so drawing the land allocates nothing. */
let scratch = { xs: new Float32Array(0), ys: new Float32Array(0), shade: new Int8Array(0) };

function drawLand(ctx: CanvasRenderingContext2D, land: readonly SpherePoint[], view: View): void {
  const size = Math.max(1.4, view.radius / 170);
  if (scratch.xs.length < land.length) {
    scratch = {
      xs: new Float32Array(land.length),
      ys: new Float32Array(land.length),
      shade: new Int8Array(land.length),
    };
  }
  const { xs, ys, shade } = scratch;
  // The same orthographic projection as globeMath.project, inlined so the view's
  // trigonometry is computed once and no per-point object is created.
  const lat0 = (view.lat * Math.PI) / 180;
  const lon0 = (view.lon * Math.PI) / 180;
  const sin0 = Math.sin(lat0);
  const cos0 = Math.cos(lat0);
  for (let index = 0; index < land.length; index += 1) {
    const point = land[index];
    if (point === undefined) continue;
    const dLon = point.lonRad - lon0;
    const cosDLon = Math.cos(dLon);
    const depth = sin0 * point.sinLat + cos0 * point.cosLat * cosDLon;
    xs[index] = view.cx + view.radius * point.cosLat * Math.sin(dLon);
    ys[index] = view.cy - view.radius * (cos0 * point.sinLat - sin0 * point.cosLat * cosDLon);
    shade[index] = depth <= 0 ? -1 : Math.min(3, Math.floor(depth * 4));
  }
  for (let band = 0; band < 4; band += 1) {
    ctx.fillStyle = `rgba(233,228,220,${0.2 + band * 0.15})`;
    for (let index = 0; index < land.length; index += 1) {
      if (shade[index] !== band) continue;
      ctx.fillRect((xs[index] ?? 0) - size / 2, (ys[index] ?? 0) - size / 2, size, size);
    }
  }
}

function drawPoints(
  ctx: CanvasRenderingContext2D,
  layer: SceneLayer,
  view: View,
  alpha: number,
  time: number,
  emphasis: boolean,
): void {
  const base = Math.max(1.6, view.radius / 120) * (emphasis ? 1.35 : 1);
  layer.points.forEach((point, index) => {
    const p = project(point, view);
    if (p.depth <= 0.02) return;
    const pulse = 0.5 + 0.5 * Math.sin(time * 2.4 + index * 1.7);
    const fade = alpha * (0.35 + 0.65 * p.depth);
    if (emphasis) {
      ctx.fillStyle = withAlpha(layer.colour, fade * 0.22 * pulse);
      ctx.beginPath();
      ctx.arc(p.x, p.y, base * (2.2 + pulse * 1.8), 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.fillStyle = withAlpha(layer.colour, fade);
    ctx.beginPath();
    ctx.arc(p.x, p.y, base, 0, Math.PI * 2);
    ctx.fill();
  });
}

function drawRoutes(
  ctx: CanvasRenderingContext2D,
  layer: SceneLayer,
  view: View,
  alpha: number,
  time: number,
): void {
  ctx.lineWidth = Math.max(1, view.radius / 260);
  layer.routes.forEach((route, routeIndex) => {
    ctx.strokeStyle = withAlpha(layer.colour, alpha * 0.45);
    ctx.beginPath();
    let open = false;
    for (const point of route) {
      const p = project(point, view);
      if (p.depth <= 0) {
        open = false;
        continue;
      }
      if (open) ctx.lineTo(p.x, p.y);
      else ctx.moveTo(p.x, p.y);
      open = true;
    }
    ctx.stroke();
    const travel = (time * 0.05 + routeIndex * 0.23) % 1;
    const point = route[Math.floor(travel * (route.length - 1))];
    const marker = point === undefined ? null : project(point, view);
    if (marker !== null && marker.depth > 0) {
      ctx.fillStyle = withAlpha(layer.colour, alpha);
      ctx.beginPath();
      ctx.arc(marker.x, marker.y, Math.max(2, view.radius / 90), 0, Math.PI * 2);
      ctx.fill();
    }
  });
}

function drawOrbits(
  ctx: CanvasRenderingContext2D,
  layer: SceneLayer,
  view: View,
  alpha: number,
  time: number,
): void {
  for (const orbit of ORBITS) {
    for (let i = 0; i < orbit.count; i += 1) {
      const angle = time * orbit.speed + orbit.phase + (i * Math.PI * 2) / orbit.count;
      const lat =
        Math.asin(Math.sin(angle) * Math.sin((orbit.tilt * Math.PI) / 180)) * (180 / Math.PI);
      const lon =
        ((Math.atan2(Math.sin(angle) * Math.cos((orbit.tilt * Math.PI) / 180), Math.cos(angle)) *
          180) /
          Math.PI +
          orbit.phase * 40) %
        360;
      const p = project(toSphere({ lat, lon: lon > 180 ? lon - 360 : lon }), {
        ...view,
        radius: view.radius * 1.12,
      });
      if (p.depth <= -0.2) continue;
      ctx.fillStyle = withAlpha(layer.colour, alpha * (p.depth > 0 ? 1 : 0.35));
      ctx.fillRect(p.x - 2, p.y - 2, 4, 4);
    }
  }
}

function drawCells(
  ctx: CanvasRenderingContext2D,
  layer: SceneLayer,
  view: View,
  alpha: number,
  kind: 'cells' | 'zones',
): void {
  const size = view.radius / (kind === 'zones' ? 7 : 40);
  for (const point of layer.points) {
    const p = project(point, view);
    if (p.depth <= 0.05) continue;
    if (kind === 'zones') {
      const halo = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, size);
      halo.addColorStop(0, withAlpha(layer.colour, alpha * 0.35));
      halo.addColorStop(1, withAlpha(layer.colour, 0));
      ctx.fillStyle = halo;
      ctx.beginPath();
      ctx.arc(p.x, p.y, size, 0, Math.PI * 2);
      ctx.fill();
    } else {
      ctx.strokeStyle = withAlpha(layer.colour, alpha * 0.8 * p.depth);
      ctx.strokeRect(p.x - size, p.y - size, size * 2, size * 2);
    }
  }
}

export function drawGlobe(
  ctx: CanvasRenderingContext2D,
  land: readonly SpherePoint[],
  layers: readonly SceneLayer[],
  frame: FrameState,
): void {
  const { view } = frame;
  drawBase(ctx, view);
  drawLand(ctx, land, view);
  layers.forEach((layer, index) => {
    const alpha = Math.min(1, Math.max(0, frame.revealed - index));
    if (alpha <= 0) return;
    const dim = frame.active >= 0 && index !== frame.active ? 0.55 : 1;
    if (layer.kind === 'points')
      drawPoints(ctx, layer, view, alpha * dim, frame.time, index === frame.active);
    else if (layer.kind === 'routes') drawRoutes(ctx, layer, view, alpha * dim, frame.time);
    else if (layer.kind === 'orbits') drawOrbits(ctx, layer, view, alpha * dim, frame.time);
    else drawCells(ctx, layer, view, alpha * dim, layer.kind);
  });
}
