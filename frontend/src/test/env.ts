/** Browser environment shims for jsdom: media queries, visibility, clipboard, WebGL. */
import { vi } from 'vitest';
import type { Mock } from 'vitest';

export function mockMatchMedia(reducedMotion: boolean): void {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: (query: string): MediaQueryList => ({
      matches: reducedMotion && query.includes('prefers-reduced-motion'),
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

export function setVisibility(state: DocumentVisibilityState): void {
  Object.defineProperty(document, 'visibilityState', {
    configurable: true,
    get: () => state,
  });
  document.dispatchEvent(new Event('visibilitychange'));
}

export function resetVisibility(): void {
  Reflect.deleteProperty(document, 'visibilityState');
}

export function mockClipboard(): { writeText: Mock<(text: string) => Promise<void>> } {
  const writeText = vi.fn<(text: string) => Promise<void>>().mockResolvedValue(undefined);
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
  return { writeText };
}

export function mockWebGl2(available: boolean): void {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(() =>
    available ? ({} as unknown as WebGL2RenderingContext) : null,
  );
}

export function setCsrfCookie(value: string): void {
  document.cookie = `ase_csrf=${value}; path=/`;
}

export function clearCookies(): void {
  for (const part of document.cookie.split(';')) {
    const name = part.split('=')[0]?.trim();
    if (name !== undefined && name !== '') {
      document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
    }
  }
}
