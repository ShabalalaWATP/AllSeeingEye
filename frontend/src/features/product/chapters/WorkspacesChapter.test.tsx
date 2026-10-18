import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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
import { SETTLE_MS } from '../motion/useHorizontalPin';
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
  let rect: MockInstance<() => DOMRect>;
  beforeEach(() => {
    roomyScreen();
    rect = vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
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
    expect(screen.getByRole('button', { name: 'Previous workspace' })).toHaveAttribute(
      'aria-disabled',
      'true',
    );

    fireEvent.click(screen.getByRole('button', { name: 'Next workspace' }));
    // Travel is 3,400 - 1,000 px; panel 2 of 7 sits a sixth of the way along it.
    expect(scrollWindow).toHaveBeenLastCalledWith({ top: 900, behavior: 'smooth' });
    expect(position()).toHaveTextContent(`Panel 2 of ${total}`);
    expect(screen.getByRole('button', { name: 'Previous workspace' })).toHaveAttribute(
      'aria-disabled',
      'false',
    );
  });

  it('keeps focus on an end button and does nothing when it is pressed', async () => {
    renderGallery(false);
    const chapter = screen.getByRole('region', { name: 'Specialist workspaces' });
    await waitFor(() => expect(chapter.style.getPropertyValue('--progress')).toBe('0.0000'));
    const previous = screen.getByRole('button', { name: 'Previous workspace' });
    previous.focus();
    fireEvent.click(previous);
    expect(scrollWindow).not.toHaveBeenCalled();
    expect(previous).toHaveFocus();

    const next = screen.getByRole('button', { name: 'Next workspace' });
    next.focus();
    for (let press = 1; press < total; press++) fireEvent.click(next);
    expect(position()).toHaveTextContent(`Panel ${total} of ${total}`);
    expect(next).toHaveAttribute('aria-disabled', 'true');
    expect(next).toBeEnabled();
    const calls = scrollWindow.mock.calls.length;
    fireEvent.click(next);
    expect(scrollWindow).toHaveBeenCalledTimes(calls);
    expect(position()).toHaveTextContent(`Panel ${total} of ${total}`);
    expect(next).toHaveFocus();
  });

  it('steps on from the chosen panel while the smooth scroll is still on its way', async () => {
    renderGallery(false);
    const chapter = screen.getByRole('region', { name: 'Specialist workspaces' });
    await waitFor(() => expect(chapter.style.getPropertyValue('--progress')).toBe('0.0000'));
    const gallery = screen.getByRole('region', { name: 'Workspace gallery' });
    fireEvent.keyDown(gallery, { key: 'ArrowRight' });
    // The scroll has barely started: its progress still rounds to the first panel.
    rect.mockReturnValue({ top: -100, height: 3400 } as DOMRect);
    fireEvent.scroll(window);
    await waitFor(() => expect(chapter.style.getPropertyValue('--progress')).toBe('0.0417'));
    expect(position()).toHaveTextContent(`Panel 2 of ${total}`);

    fireEvent.keyDown(gallery, { key: 'ArrowRight' });
    expect(position()).toHaveTextContent(`Panel 3 of ${total}`);
    // Panel 3 sits a third of the way along the 2,400 px travel from the section's top.
    expect(scrollWindow).toHaveBeenLastCalledWith({ top: 700, behavior: 'smooth' });

    // Once the scroll ends, the position follows wherever the track really stopped.
    rect.mockReturnValue({ top: -800, height: 3400 } as DOMRect);
    fireEvent.scroll(window);
    await waitFor(() => expect(chapter.style.getPropertyValue('--progress')).toBe('0.3333'));
    fireEvent(window, new Event('scrollend'));
    expect(position()).toHaveTextContent(`Panel 3 of ${total}`);
    rect.mockReturnValue({ top: -400, height: 3400 } as DOMRect);
    fireEvent.scroll(window);
    await waitFor(() => expect(position()).toHaveTextContent(`Panel 2 of ${total}`));
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
    expect(screen.getByRole('button', { name: 'Next workspace' })).toHaveAttribute(
      'aria-disabled',
      'true',
    );
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

    // The row settles on the chosen panel, then follows swipes again.
    fireEvent(viewport!, new Event('scrollend'));
    Object.defineProperty(viewport, 'scrollLeft', { configurable: true, value: 1210 });
    fireEvent.scroll(viewport!);
    await waitFor(() => expect(position()).toHaveTextContent(`Panel 4 of ${total}`));
  });

  it('ignores its own smooth scroll until it settles, even where scrollend never fires', () => {
    vi.useFakeTimers();
    try {
      const { container } = renderGallery(false);
      const viewport = container.querySelector<HTMLElement>('.workspaces-viewport')!;
      screen
        .getAllByRole('group')
        .forEach((slide, index) =>
          Object.defineProperty(slide, 'offsetLeft', { configurable: true, value: index * 400 }),
        );
      const gallery = screen.getByRole('region', { name: 'Workspace gallery' });
      fireEvent.keyDown(gallery, { key: 'ArrowRight' });
      Object.defineProperty(viewport, 'scrollLeft', { configurable: true, value: 120 });
      fireEvent.scroll(viewport);
      act(() => {
        vi.advanceTimersByTime(20);
      });
      expect(position()).toHaveTextContent(`Panel 2 of ${total}`);
      fireEvent.keyDown(gallery, { key: 'ArrowRight' });
      expect(scrollViewport).toHaveBeenLastCalledWith({ left: 800, behavior: 'smooth' });
      expect(position()).toHaveTextContent(`Panel 3 of ${total}`);

      act(() => {
        vi.advanceTimersByTime(SETTLE_MS);
      });
      Object.defineProperty(viewport, 'scrollLeft', { configurable: true, value: 1610 });
      fireEvent.scroll(viewport);
      act(() => {
        vi.advanceTimersByTime(20);
      });
      expect(position()).toHaveTextContent(`Panel 5 of ${total}`);
    } finally {
      vi.useRealTimers();
    }
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
