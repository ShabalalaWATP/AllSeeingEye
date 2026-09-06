/**
 * Resolves where to send a user after login. Only same-origin absolute paths are
 * honoured; anything else (external URLs, protocol-relative paths, missing state)
 * falls back to the supplied landing page (the globe by default).
 */
export function redirectTarget(state: unknown, fallback = '/'): string {
  if (typeof state === 'object' && state !== null && 'from' in state) {
    const from: unknown = state.from;
    if (typeof from === 'string' && from.startsWith('/') && !from.startsWith('//')) {
      return from;
    }
  }
  return fallback;
}
