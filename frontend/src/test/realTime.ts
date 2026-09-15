import { act } from '@testing-library/react';

// Captured at import, before a test installs fake timers.
const realTimeout = globalThis.setTimeout;

/**
 * Retry a check in real time and return its result. RTL's async helpers wait on a
 * zero-delay timer that fake timers never fire, and vi.waitFor advances the fake clock,
 * which would blur interval assertions in polling tests.
 */
export async function untilReal<T>(check: () => T, attempts = 300): Promise<T> {
  for (let attempt = 0; ; attempt += 1) {
    try {
      return check();
    } catch (error) {
      if (attempt >= attempts) throw error;
      await act(() => new Promise<void>((resolve) => realTimeout(resolve, 10)));
    }
  }
}
