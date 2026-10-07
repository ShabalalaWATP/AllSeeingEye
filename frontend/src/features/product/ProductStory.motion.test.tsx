import { render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';

import { ProductStory } from './ProductStory';

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
