import { act, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { DrawPath } from './DrawPath';
import { Reveal, type RevealVariant } from './Reveal';
import { StoryMotionContext } from './useStoryMotion';

type Callback = (entries: { isIntersecting: boolean }[]) => void;

function installObserver(): { enter: () => void } {
  let callback: Callback = () => undefined;
  class FakeObserver {
    constructor(next: Callback) {
      callback = next;
    }
    observe = vi.fn();
    disconnect = vi.fn();
  }
  vi.stubGlobal('IntersectionObserver', FakeObserver);
  return { enter: () => callback([{ isIntersecting: true }]) };
}

function renderReveal(still: boolean, variant?: RevealVariant) {
  return render(
    <StoryMotionContext.Provider value={{ still, idle: still }}>
      {variant ? (
        <Reveal variant={variant}>Frozen evidence</Reveal>
      ) : (
        <Reveal>Frozen evidence</Reveal>
      )}
    </StoryMotionContext.Provider>,
  );
}

const shown = () => screen.getByText('Frozen evidence');

describe('Reveal', () => {
  afterEach(() => vi.unstubAllGlobals());

  it.each(['rise', 'fade', 'mask'] as const)(
    'waits for the viewport, then shows a %s reveal',
    (variant) => {
      const observer = installObserver();
      renderReveal(false, variant);
      expect(shown()).toHaveAttribute('data-variant', variant);
      expect(shown()).toHaveAttribute('data-shown', 'false');
      act(() => observer.enter());
      expect(shown()).toHaveAttribute('data-shown', 'true');
    },
  );

  it('rises by default and shows every variant at once when the story is still', () => {
    installObserver();
    const { unmount } = renderReveal(true);
    expect(shown()).toHaveAttribute('data-variant', 'rise');
    expect(shown()).toHaveAttribute('data-shown', 'true');
    unmount();
    renderReveal(true, 'mask');
    expect(shown()).toHaveAttribute('data-shown', 'true');
  });
});

describe('DrawPath', () => {
  it('normalises the stroke and passes its timing to CSS', () => {
    const { container } = render(
      <svg aria-hidden="true">
        <DrawPath d="M 0 0 L 10 10" start={0.25} rate={4} className="thread" />
      </svg>,
    );
    const path = container.querySelector('path');
    expect(path).toHaveAttribute('pathLength', '1');
    expect(path).toHaveClass('draw-path', 'thread');
    expect(path?.style.getPropertyValue('--draw-start')).toBe('0.25');
    expect(path?.style.getPropertyValue('--draw-rate')).toBe('4');
  });
});
