import { act, render, screen } from '@testing-library/react';
import { createRef, type RefObject } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { fakeContext } from '@/test/fakeCanvas';

import { StoryMotionContext, type StoryMotion } from '../motion/useStoryMotion';
import { GlobeCanvas, type GlobeControls } from './GlobeCanvas';

type Observed = (entries: { isIntersecting: boolean }[]) => void;

let frames: Map<number, FrameRequestCallback>;
let nextFrame: number;
let intersect: Observed;
let resized: () => void;
let noContext = false;

function runFrames(times: number, step = 16): void {
  let now = performance.now();
  for (let i = 0; i < times; i += 1) {
    const pending = [...frames.entries()];
    frames.clear();
    now += step;
    for (const [, callback] of pending) callback(now);
  }
}

function controls(values: GlobeControls): RefObject<GlobeControls> {
  const ref = createRef<GlobeControls>() as { current: GlobeControls };
  ref.current = values;
  return ref;
}

function renderGlobe(motion: StoryMotion, ref = controls({ revealed: 4, active: 2, focus: 0 })) {
  const view = render(
    <StoryMotionContext.Provider value={motion}>
      <GlobeCanvas controls={ref} label="Illustrative globe" />
    </StoryMotionContext.Provider>,
  );
  return { ...view, ref };
}

describe('GlobeCanvas', () => {
  let drawn: ReturnType<typeof fakeContext>;

  beforeEach(() => {
    drawn = fakeContext();
    frames = new Map();
    nextFrame = 0;
    noContext = false;
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(() =>
      noContext ? null : drawn.ctx,
    );
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
      nextFrame += 1;
      frames.set(nextFrame, callback);
      return nextFrame;
    });
    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation((id) => {
      frames.delete(id);
    });
    vi.stubGlobal(
      'IntersectionObserver',
      class {
        constructor(callback: Observed) {
          intersect = callback;
        }
        observe = vi.fn();
        disconnect = vi.fn();
      },
    );
    vi.stubGlobal(
      'ResizeObserver',
      class {
        constructor(callback: () => void) {
          resized = callback;
        }
        observe = vi.fn();
        disconnect = vi.fn();
      },
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('is an image with a description, not an interactive canvas', () => {
    renderGlobe({ still: true, idle: true });
    expect(screen.getByRole('img', { name: 'Illustrative globe' })).toBeInTheDocument();
  });

  it('draws one complete frame and no loop when the story is still', () => {
    renderGlobe({ still: true, idle: true });
    expect(drawn.counts.clearRect).toBe(1);
    expect(frames.size).toBe(0);
  });

  it('keeps turning while visible, stops off screen and resumes on return', () => {
    const { ref } = renderGlobe({ still: false, idle: false });
    runFrames(3);
    const painted = drawn.counts.clearRect ?? 0;
    expect(painted).toBeGreaterThan(2);
    act(() => intersect([{ isIntersecting: false }]));
    runFrames(2);
    expect(frames.size).toBe(0);
    ref.current.focus = 1;
    act(() => intersect([{ isIntersecting: true }]));
    expect(frames.size).toBe(1);
    runFrames(2, 200);
    expect(drawn.counts.clearRect).toBeGreaterThan(painted + 1);
  });

  it('repaints on resize and stops cleanly when unmounted', () => {
    const { unmount } = renderGlobe({ still: false, idle: false });
    const before = drawn.counts.clearRect ?? 0;
    act(() => resized());
    expect(drawn.counts.clearRect).toBe(before + 1);
    expect(drawn.counts.setTransform).toBeGreaterThan(1);
    unmount();
    expect(frames.size).toBe(0);
  });

  it('pauses when the story goes idle and wakes without resetting', () => {
    const ref = controls({ revealed: 15, active: 3, focus: 0.5 });
    const view = renderGlobe({ still: false, idle: false }, ref);
    runFrames(1);
    view.rerender(
      <StoryMotionContext.Provider value={{ still: false, idle: true }}>
        <GlobeCanvas controls={ref} label="Illustrative globe" />
      </StoryMotionContext.Provider>,
    );
    runFrames(1);
    expect(frames.size).toBe(0);
    view.rerender(
      <StoryMotionContext.Provider value={{ still: false, idle: false }}>
        <GlobeCanvas controls={ref} label="Illustrative globe" />
      </StoryMotionContext.Provider>,
    );
    expect(frames.size).toBe(1);
  });

  it('copes with a browser that has no canvas context or observers', () => {
    vi.unstubAllGlobals();
    vi.stubGlobal('IntersectionObserver', undefined);
    vi.stubGlobal('ResizeObserver', undefined);
    renderGlobe({ still: false, idle: false });
    expect(drawn.counts.clearRect).toBeGreaterThan(0);
    noContext = true;
    expect(() => renderGlobe({ still: false, idle: false })).not.toThrow();
  });
});
