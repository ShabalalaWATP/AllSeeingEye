import { render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { renderApp } from '@/test/render';

import { AssistantEye } from './AssistantEye';
import { BrandMark } from './BrandMark';
import EvilEye from './EvilEye';

// Real component: jsdom has no WebGL, so each instance keeps its captured fallback.
vi.unmock('./EvilEye');

function fallback(container: HTMLElement) {
  const image = container.querySelector('picture img');
  const webp = container.querySelector('picture source[type="image/webp"]');
  if (image === null || webp === null) throw new Error('fallback capture missing');
  return { image, webp };
}

describe('Evil Eye captured fallback', () => {
  it('offers small and large captures of the real eye and decodes them off the main thread', () => {
    const { container } = render(<EvilEye />);
    const { image, webp } = fallback(container);
    expect(image).toHaveAttribute('src', '/brand/eye-512.png');
    expect(image).toHaveAttribute('decoding', 'async');
    expect(image.getAttribute('srcset')).toContain('/brand/eye-64.png 64w');
    expect(image.getAttribute('srcset')).toContain('/brand/eye-128.png 128w');
    expect(image.getAttribute('srcset')).toContain('/brand/eye-512.png 512w');
    expect(webp.getAttribute('srcset')).toContain('/brand/eye-64.webp 64w');
    expect(webp.getAttribute('srcset')).toContain('/brand/eye-512.webp 512w');
  });

  it('sizes the rail and loading marks to their rendered height', () => {
    const { container } = render(<BrandMark size={38} />);
    const { image, webp } = fallback(container);
    expect(image).toHaveAttribute('sizes', '38px');
    expect(webp).toHaveAttribute('sizes', '38px');
  });

  it('sizes the assistant launcher to its 64 px mark', () => {
    const { container } = render(<AssistantEye />);
    expect(fallback(container).image).toHaveAttribute('sizes', '64px');
  });

  it('keeps the large capture for the sign-in brand plane', () => {
    const { container } = renderApp('/login', 'anonymous');
    const sizes = fallback(container).image.getAttribute('sizes') ?? '';
    expect(sizes).toMatch(/480px$/);
  });
});
