import { describe, expect, it } from 'vitest';

import { fakeContext } from '@/test/fakeCanvas';

import { drawGlobe, type FrameState } from './drawGlobe';
import { landPoints, toSphere } from './globeMath';
import { buildScene, type SceneLayer } from './sceneData';

const land = landPoints(3000);
const layers = buildScene();

function frame(overrides: Partial<FrameState> = {}): FrameState {
  return {
    view: { lon: 30, lat: 15, radius: 200, cx: 250, cy: 250 },
    revealed: layers.length,
    active: 0,
    time: 1.5,
    ...overrides,
  };
}

describe('drawGlobe', () => {
  it('draws only the atmosphere, ocean and land before any layer is revealed', () => {
    const { ctx, counts } = fakeContext();
    drawGlobe(ctx, land, layers, frame({ revealed: 0 }));
    expect(counts.createRadialGradient).toBe(2);
    expect(counts.fillRect).toBeGreaterThan(100);
    expect(counts.strokeRect ?? 0).toBe(0);
    expect(counts.moveTo ?? 0).toBe(0);
  });

  it('draws every kind of layer once revealed, from every side of the Earth', () => {
    for (const lon of [-150, -60, 30, 120]) {
      for (const active of [-1, 0, 6, 12]) {
        const { ctx, counts } = fakeContext();
        drawGlobe(
          ctx,
          land,
          layers,
          frame({ view: { lon, lat: 20, radius: 180, cx: 200, cy: 200 }, active, time: lon + 100 }),
        );
        expect(counts.arc, `points at ${lon}`).toBeGreaterThan(0);
        expect(counts.moveTo, `routes at ${lon}`).toBeGreaterThan(0);
        expect(counts.stroke, `route lines at ${lon}`).toBeGreaterThan(0);
      }
    }
  });

  it('fades the newest layer in and leaves later layers undrawn', () => {
    const partial = fakeContext();
    drawGlobe(partial.ctx, land, layers, frame({ revealed: 1.5, active: 1 }));
    const full = fakeContext();
    drawGlobe(full.ctx, land, layers, frame());
    expect(partial.counts.moveTo ?? 0).toBe(0);
    expect(partial.counts.arc).toBeLessThan(full.counts.arc ?? 0);
  });

  it('draws interference cells as squares and conflict regions as soft zones', () => {
    const cells: SceneLayer = {
      id: 'interference',
      kind: 'cells',
      colour: '#f5b53f',
      points: [toSphere({ lat: 15, lon: 30 })],
      routes: [],
    };
    const zones: SceneLayer = { ...cells, id: 'regions', kind: 'zones' };
    const { ctx, counts } = fakeContext();
    drawGlobe(ctx, [], [cells, zones], frame({ active: -1 }));
    expect(counts.strokeRect).toBe(1);
    expect(counts.createRadialGradient).toBe(3);
  });

  it('skips points and markers on the far side of the globe', () => {
    const far = toSphere({ lat: -15, lon: -150 });
    const hidden: SceneLayer[] = [
      { id: 'conflict', kind: 'points', colour: '#ff5a5a', points: [far], routes: [] },
      { id: 'aircraft', kind: 'routes', colour: '#f5b53f', points: [], routes: [[far, far]] },
      { id: 'grid', kind: 'cells', colour: '#9aa3b2', points: [far], routes: [] },
    ];
    const { ctx, counts } = fakeContext();
    drawGlobe(ctx, [], hidden, frame());
    // Only the atmosphere and ocean discs.
    expect(counts.arc).toBe(2);
    expect(counts.moveTo ?? 0).toBe(0);
    expect(counts.strokeRect ?? 0).toBe(0);
  });

  it('reuses its buffers when the land grows between frames', () => {
    const small = fakeContext();
    drawGlobe(small.ctx, land.slice(0, 50), [], frame());
    const large = fakeContext();
    drawGlobe(large.ctx, landPoints(6000), [], frame());
    expect(large.counts.fillRect).toBeGreaterThan(small.counts.fillRect ?? 0);
  });
});
