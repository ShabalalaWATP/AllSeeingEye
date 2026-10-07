import { act, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { CountUp } from './CountUp';
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

function renderCount(still: boolean) {
  return render(
    <StoryMotionContext.Provider value={{ still, idle: still }}>
      <CountUp value={423} suffix="+" />
    </StoryMotionContext.Provider>,
  );
}

describe('CountUp', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('waits at zero until it scrolls into view, then counts to the value', async () => {
    const observer = installObserver();
    vi.useFakeTimers({ toFake: ['requestAnimationFrame', 'performance'] });
    renderCount(false);
    const visible = () => document.querySelector('[aria-hidden="true"]')?.textContent;
    expect(visible()).toBe('0+');
    act(() => observer.enter());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1200);
    });
    expect(visible()).toBe('423+');
    vi.useRealTimers();
  });

  it('shows the final value at once when the story is still, and always to screen readers', () => {
    installObserver();
    renderCount(true);
    expect(document.querySelector('[aria-hidden="true"]')?.textContent).toBe('423+');
    expect(screen.getByText('423+', { selector: '.sr-only' })).toBeInTheDocument();
  });
});
