import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  clamp01,
  passProgress,
  pinnedProgress,
  segment,
  subscribeScroll,
  subscriberCount,
} from './scrollScheduler';

describe('scroll progress', () => {
  it('measures a pinned section from its top meeting the viewport to its end', () => {
    expect(pinnedProgress(100, 3000, 1000)).toBe(0);
    expect(pinnedProgress(0, 3000, 1000)).toBe(0);
    expect(pinnedProgress(-1000, 3000, 1000)).toBe(0.5);
    expect(pinnedProgress(-2000, 3000, 1000)).toBe(1);
    expect(pinnedProgress(-5000, 3000, 1000)).toBe(1);
  });

  it('treats a section no taller than the viewport as all or nothing', () => {
    expect(pinnedProgress(10, 800, 1000)).toBe(0);
    expect(pinnedProgress(-1, 800, 1000)).toBe(1);
  });

  it('measures a passing element from entering at the bottom to leaving at the top', () => {
    expect(passProgress(1000, 500, 1000)).toBe(0);
    expect(passProgress(-500, 500, 1000)).toBe(1);
    expect(passProgress(250, 500, 1000)).toBe(0.5);
  });

  it('maps a window of progress onto a beat and clamps everything', () => {
    expect(segment(0.5, 0.25, 0.75)).toBe(0.5);
    expect(segment(0.1, 0.25, 0.75)).toBe(0);
    expect(segment(0.9, 0.25, 0.75)).toBe(1);
    expect(segment(0.5, 0.5, 0.5)).toBe(1);
    expect(clamp01(Number.NaN)).toBe(0);
    expect(clamp01(2)).toBe(1);
  });
});

describe('scroll scheduler', () => {
  afterEach(() => vi.restoreAllMocks());

  it('measures every subscriber before applying any, once per frame', () => {
    const frames: FrameRequestCallback[] = [];
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
      frames.push(callback);
      return frames.length;
    });
    const order: string[] = [];
    const stopA = subscribeScroll({
      measure: () => order.push('measure a'),
      apply: () => order.push('apply a'),
    });
    const stopB = subscribeScroll({
      measure: () => order.push('measure b'),
      apply: () => order.push('apply b'),
    });
    window.dispatchEvent(new Event('scroll'));
    window.dispatchEvent(new Event('scroll'));
    expect(frames).toHaveLength(1);
    frames[0]!(0);
    expect(order).toEqual(['measure a', 'measure b', 'apply a', 'apply b']);
    stopA();
    stopB();
    expect(subscriberCount()).toBe(0);
  });

  it('removes its listeners when the last subscriber leaves', () => {
    vi.spyOn(window, 'requestAnimationFrame').mockReturnValue(1);
    const cancel = vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => undefined);
    const remove = vi.spyOn(window, 'removeEventListener');
    const stop = subscribeScroll({ measure: () => 1, apply: () => undefined });
    stop();
    expect(remove).toHaveBeenCalledWith('scroll', expect.any(Function));
    expect(remove).toHaveBeenCalledWith('resize', expect.any(Function));
    expect(cancel).toHaveBeenCalledWith(1);
  });
});
