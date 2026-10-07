/**
 * Test support: a 2D canvas context that records what was drawn, for jsdom and
 * node, which have no canvas. Never import this from application code.
 */
export interface FakeContext {
  ctx: CanvasRenderingContext2D;
  counts: Record<string, number>;
}

export function fakeContext(): FakeContext {
  const counts: Record<string, number> = {};
  const record =
    (name: string) =>
    (..._args: unknown[]) => {
      counts[name] = (counts[name] ?? 0) + 1;
    };
  const gradient = { addColorStop: record('addColorStop') };
  const ctx = {
    fillStyle: '',
    strokeStyle: '',
    lineWidth: 1,
    arc: record('arc'),
    beginPath: record('beginPath'),
    clearRect: record('clearRect'),
    fill: record('fill'),
    fillRect: record('fillRect'),
    lineTo: record('lineTo'),
    moveTo: record('moveTo'),
    setTransform: record('setTransform'),
    stroke: record('stroke'),
    strokeRect: record('strokeRect'),
    createRadialGradient: (...args: unknown[]) => {
      record('createRadialGradient')(...args);
      return gradient;
    },
  };
  return { ctx: ctx as unknown as CanvasRenderingContext2D, counts };
}
