/**
 * Browser storage for per-browser conveniences. Storage can be blocked, full or cleared at
 * any time (private windows, site-data settings), so every access is guarded and callers
 * always fall back to an in-memory default.
 */
import type { StateStorage } from 'zustand/middleware';

export function readStored(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeStored(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // A lost convenience value is harmless; the in-memory state stays correct.
  }
}

function removeStored(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // Nothing to clean up when storage is unavailable.
  }
}

/** Zustand `persist` storage that never throws into a state update. */
export const safeLocalStorage: StateStorage = {
  getItem: readStored,
  setItem: writeStored,
  removeItem: removeStored,
};
