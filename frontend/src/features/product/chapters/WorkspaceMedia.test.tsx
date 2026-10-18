import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest';

import { mockMatchMedia } from '@/test/env';

import { WORKSPACES, type Workspace } from '../content/platform';
import { StoryMotionContext } from '../motion/useStoryMotion';
import { WorkspacesChapter } from './WorkspacesChapter';

function renderGallery(still: boolean, panels: readonly Workspace[]) {
  return render(
    <StoryMotionContext.Provider value={{ still, idle: still }}>
      <div className="product-story" data-motion={still ? 'still' : 'moving'}>
        <WorkspacesChapter panels={panels} />
      </div>
    </StoryMotionContext.Provider>,
  );
}

describe('workspace media', () => {
  const image: Workspace = {
    ...WORKSPACES[0]!,
    id: 'image-panel',
    media: { src: '/fake.webp', alt: 'Synthetic tracker', width: 800, height: 500, kind: 'image' },
  };
  const loop: Workspace = {
    ...WORKSPACES[1]!,
    id: 'loop-panel',
    media: {
      src: '/fake.webm',
      alt: 'Synthetic loop',
      width: 800,
      height: 450,
      kind: 'video',
      poster: '/fake-poster.webp',
    },
  };
  let play: Mock<() => Promise<void>>;
  let pause: Mock<() => void>;
  let enter: () => void = () => undefined;

  beforeEach(() => {
    mockMatchMedia(false);
    play = vi.fn(() => Promise.resolve());
    pause = vi.fn(() => undefined);
    vi.spyOn(HTMLMediaElement.prototype, 'play').mockImplementation(play);
    vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(pause);
    class FakeObserver {
      constructor(callback: (entries: { isIntersecting: boolean }[]) => void) {
        enter = () => callback([{ isIntersecting: true }]);
      }
      observe = vi.fn();
      disconnect = vi.fn();
    }
    vi.stubGlobal('IntersectionObserver', FakeObserver);
  });
  afterEach(() => {
    cleanup(); // Unmount (which pauses the loop) while play and pause are still mocked.
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('loads images lazily at their declared size with an illustrative caption', () => {
    renderGallery(true, [image]);
    const img = screen.getByRole('img', { name: 'Synthetic tracker' });
    expect(img).toHaveAttribute('width', '800');
    expect(img).toHaveAttribute('height', '500');
    expect(img).toHaveAttribute('loading', 'lazy');
    expect(img).toHaveAttribute('decoding', 'async');
    expect(screen.getByText('Illustrative screenshot')).toBeInTheDocument();
  });

  it('keeps loops muted, inline, unloaded and paused while the story is still', () => {
    const { container } = renderGallery(true, [loop]);
    const video = container.querySelector('video')!;
    expect(video.muted).toBe(true);
    expect(video).toHaveAttribute('playsinline');
    expect(video).toHaveAttribute('loop');
    expect(video).toHaveAttribute('preload', 'none');
    expect(video).toHaveAttribute('poster', '/fake-poster.webp');
    expect(video).not.toHaveAttribute('controls');
    expect(video).not.toHaveAttribute('autoplay');
    expect(pause).toHaveBeenCalled();
    expect(play).not.toHaveBeenCalled();
    expect(screen.getByText('Illustrative loop')).toBeInTheDocument();
  });

  it('plays a loop only once it is on screen while the story moves', () => {
    renderGallery(false, [loop]);
    expect(play).not.toHaveBeenCalled();
    enter();
    expect(play).toHaveBeenCalledTimes(1);
  });
});
