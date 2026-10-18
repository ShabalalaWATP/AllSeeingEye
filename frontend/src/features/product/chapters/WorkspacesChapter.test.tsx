import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
  type Mock,
  type MockInstance,
} from 'vitest';

import { mockMatchMedia } from '@/test/env';

import { WORKSPACES, type Workspace } from '../content/platform';
import { StoryMotionContext } from '../motion/useStoryMotion';
import { WorkspacesChapter } from './WorkspacesChapter';

function roomyScreen(): void {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: (query: string): MediaQueryList =>
      ({
        matches: !query.includes('prefers-reduced-motion'),
        media: query,
        onchange: null,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
        addListener: () => undefined,
        removeListener: () => undefined,
        dispatchEvent: () => false,
      }) as MediaQueryList,
  });
}

function renderGallery(still: boolean, panels?: readonly Workspace[]) {
  return render(
    <StoryMotionContext.Provider value={{ still, idle: still }}>
      <div className="product-story" data-motion={still ? 'still' : 'moving'}>
        {panels ? <WorkspacesChapter panels={panels} /> : <WorkspacesChapter />}
      </div>
    </StoryMotionContext.Provider>,
  );
}

const position = () => screen.getByText(/^Panel \d of \d$/);
const total = WORKSPACES.length;

describe('workspace gallery while pinned', () => {
  const offsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');
  let scrollWindow: MockInstance<typeof window.scrollTo>;
  beforeEach(() => {
    roomyScreen();
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
      top: 500,
      height: 3400,
    } as DOMRect);
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
      configurable: true,
      get: () => 1000,
    });
    scrollWindow = vi.spyOn(window, 'scrollTo').mockImplementation(() => undefined);
  });
  afterEach(() => {
    vi.restoreAllMocks();
    if (offsetHeight) Object.defineProperty(HTMLElement.prototype, 'offsetHeight', offsetHeight);
    mockMatchMedia(false);
  });

  it('moves between panels with the buttons by scrolling to each panel’s progress', async () => {
    renderGallery(false);
    const chapter = screen.getByRole('region', { name: 'Specialist workspaces' });
    expect(chapter).toHaveAttribute('data-mode', 'pinned');
    await waitFor(() => expect(chapter.style.getPropertyValue('--progress')).toBe('0.0000'));
    const gallery = screen.getByRole('region', { name: 'Workspace gallery' });
    expect(gallery).toHaveAttribute('aria-roledescription', 'carousel');
    expect(position()).toHaveTextContent(`Panel 1 of ${total}`);
    expect(position()).toHaveAttribute('aria-live', 'polite');
    expect(screen.getByRole('button', { name: 'Previous workspace' })).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: 'Next workspace' }));
    // Travel is 3,400 - 1,000 px; panel 2 of 7 sits a sixth of the way along it.
    expect(scrollWindow).toHaveBeenLastCalledWith({ top: 900, behavior: 'smooth' });
    expect(position()).toHaveTextContent(`Panel 2 of ${total}`);
    expect(screen.getByRole('button', { name: 'Previous workspace' })).toBeEnabled();
  });

  it('moves with the arrow keys on the focusable gallery and stops at either end', async () => {
    renderGallery(false);
    const chapter = screen.getByRole('region', { name: 'Specialist workspaces' });
    await waitFor(() => expect(chapter.style.getPropertyValue('--progress')).toBe('0.0000'));
    const gallery = screen.getByRole('region', { name: 'Workspace gallery' });
    expect(gallery).toHaveAttribute('tabindex', '0');
    fireEvent.keyDown(gallery, { key: 'ArrowRight' });
    fireEvent.keyDown(gallery, { key: 'ArrowRight' });
    expect(scrollWindow).toHaveBeenLastCalledWith({ top: 1300, behavior: 'smooth' });
    expect(position()).toHaveTextContent(`Panel 3 of ${total}`);
    fireEvent.keyDown(gallery, { key: 'ArrowLeft' });
    expect(position()).toHaveTextContent(`Panel 2 of ${total}`);
    for (let press = 0; press < total + 2; press++)
      fireEvent.keyDown(gallery, { key: 'ArrowRight' });
    expect(scrollWindow).toHaveBeenLastCalledWith({ top: 2900, behavior: 'smooth' });
    expect(position()).toHaveTextContent(`Panel ${total} of ${total}`);
    expect(screen.getByRole('button', { name: 'Next workspace' })).toBeDisabled();
  });

  it('labels each panel as a slide in visual order', () => {
    renderGallery(false);
    const slides = screen.getAllByRole('group');
    expect(slides).toHaveLength(total);
    slides.forEach((slide, index) => {
      expect(slide).toHaveAttribute('aria-roledescription', 'slide');
      expect(slide).toHaveAccessibleName(`${index + 1} of ${total}`);
      expect(within(slide).getByRole('heading', { level: 3 })).toHaveTextContent(
        WORKSPACES[index]?.name ?? '',
      );
    });
  });
});

describe('workspace gallery as a swipe row', () => {
  let scrollViewport: Mock<(options?: ScrollToOptions) => void>;
  beforeEach(() => {
    mockMatchMedia(false);
    scrollViewport = vi.fn<(options?: ScrollToOptions) => void>();
    Element.prototype.scrollTo = scrollViewport as typeof Element.prototype.scrollTo;
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
      window.setTimeout(() => callback(0), 0);
      return 1;
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
    Reflect.deleteProperty(Element.prototype, 'scrollTo');
  });

  it('scrolls its own viewport to the panel and follows swipes', async () => {
    const { container } = renderGallery(false);
    expect(screen.getByRole('region', { name: 'Specialist workspaces' })).toHaveAttribute(
      'data-mode',
      'passing',
    );
    const viewport = container.querySelector<HTMLElement>('.workspaces-viewport');
    const slides = screen.getAllByRole('group');
    slides.forEach((slide, index) =>
      Object.defineProperty(slide, 'offsetLeft', { configurable: true, value: index * 400 }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Next workspace' }));
    expect(scrollViewport).toHaveBeenLastCalledWith({ left: 400, behavior: 'smooth' });
    expect(position()).toHaveTextContent(`Panel 2 of ${total}`);

    Object.defineProperty(viewport, 'scrollLeft', { configurable: true, value: 1210 });
    fireEvent.scroll(viewport!);
    await waitFor(() => expect(position()).toHaveTextContent(`Panel 4 of ${total}`));
  });
});

describe('workspace gallery when the story is still', () => {
  it('becomes a plain vertical list with no carousel controls', () => {
    const { container } = renderGallery(true);
    expect(screen.getByRole('region', { name: 'Specialist workspaces' })).toHaveAttribute(
      'data-mode',
      'still',
    );
    expect(screen.queryByRole('region', { name: 'Workspace gallery' })).toBeNull();
    expect(screen.queryByRole('button')).toBeNull();
    expect(container.querySelector('[tabindex]')).toBeNull();
    const track = container.querySelector<HTMLElement>('.workspace-track');
    expect(track).toHaveAttribute('role', 'list');
    expect(track?.style.transform).toBe('');
    const items = [...(track?.children ?? [])];
    expect(items).toHaveLength(total);
    for (const item of items) expect(item).toHaveAttribute('role', 'listitem');
  });

  it('describes map tools and states each honest limit', () => {
    renderGallery(true);
    expect(screen.getByRole('heading', { name: 'Map tools' })).toBeInTheDocument();
    for (const workspace of WORKSPACES) {
      expect(workspace.body.split(/(?<=\.)\s/).length).toBeLessThanOrEqual(2);
      if (workspace.limit) expect(screen.getByText(workspace.limit)).toBeInTheDocument();
    }
    expect(WORKSPACES.filter((workspace) => workspace.limit).length).toBeGreaterThanOrEqual(5);
  });
});

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
