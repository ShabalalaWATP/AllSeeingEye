import { render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ProductStory } from './ProductStory';

function screenSize(roomy: boolean): void {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: (query: string): MediaQueryList =>
      ({
        matches: !query.includes('prefers-reduced-motion') && (roomy || !query.includes('900px')),
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
const roomyScreen = () => screenSize(true);

afterEach(() => {
  vi.restoreAllMocks();
});

describe('product story on a wide screen', () => {
  it('pins the scroll chapters and writes their progress as the reader scrolls', async () => {
    roomyScreen();
    const { container } = render(
      <MemoryRouter>
        <ProductStory />
      </MemoryRouter>,
    );
    const observe = container.querySelector<HTMLElement>('#observe');
    expect(observe).toHaveAttribute('data-mode', 'pinned');
    expect(observe?.style.height).toMatch(/svh$/);
    expect(container.querySelector('#workspaces')).toHaveAttribute('data-mode', 'pinned');
    // Tall chapters never pin; they play their motion as they pass.
    expect(container.querySelector('#sources')).toHaveAttribute('data-mode', 'passing');
    expect(container.querySelector('#deploy')).toHaveAttribute('data-mode', 'passing');

    window.dispatchEvent(new Event('scroll'));
    await waitFor(() => expect(observe?.style.getPropertyValue('--progress')).not.toBe(''));
    const track = container.querySelector<HTMLElement>('.workspace-track');
    await waitFor(() => expect(track?.style.transform).toMatch(/translate3d/));
    expect(container.querySelector('.product-story')).toHaveAttribute('data-motion', 'moving');
  });
});

describe('product story on a narrow screen', () => {
  it('pins no chapter, the hero and Observe included, and plays the motion in passing', async () => {
    screenSize(false);
    let heroTop = 0;
    const realRect = Element.prototype.getBoundingClientRect;
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function (
      this: Element,
    ) {
      if (this.id !== 'top') return realRect.call(this);
      return new DOMRect(0, heroTop, 375, window.innerHeight);
    });
    const { container } = render(
      <MemoryRouter>
        <ProductStory />
      </MemoryRouter>,
    );
    const sections = [...container.querySelectorAll<HTMLElement>('section[data-mode]')];
    expect(sections.length).toBeGreaterThan(8);
    for (const section of sections) {
      expect(section.dataset.mode, section.id).not.toBe('pinned');
      expect(section.style.height, section.id).toBe('');
    }
    const hero = container.querySelector<HTMLElement>('#top');
    expect(hero).toHaveAttribute('data-mode', 'passing');
    expect(container.querySelector('#observe')).toHaveAttribute('data-mode', 'passing');
    // In view at load, the hero holds its opening frame; it has dissolved once it has gone.
    window.dispatchEvent(new Event('scroll'));
    await waitFor(() => expect(hero?.style.getPropertyValue('--progress')).toBe('0.0000'));
    heroTop = -window.innerHeight;
    window.dispatchEvent(new Event('scroll'));
    await waitFor(() => expect(hero?.style.getPropertyValue('--progress')).toBe('1.0000'));
  });
});
