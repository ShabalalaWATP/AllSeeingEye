/** Device-only animation preference; public pages never load account stores. */
import { readStored } from '@/lib/safeStorage';

export const MOTION_STORAGE_KEY = 'ase.brand-motion';

// --- Device choice (pre-sign-in) -------------------------------------------------

const localListeners = new Set<() => void>();
let storageAvailable = true;
let memoryPaused = false;

function notifyLocal(): void {
  for (const listener of localListeners) listener();
}

export function subscribeLocalPause(onChange: () => void): () => void {
  localListeners.add(onChange);
  window.addEventListener('storage', onChange);
  return () => {
    localListeners.delete(onChange);
    window.removeEventListener('storage', onChange);
  };
}

export function readLocalPause(): boolean {
  return storageAvailable ? readStored(MOTION_STORAGE_KEY) === 'paused' : memoryPaused;
}

export function writeLocalPause(paused: boolean): void {
  memoryPaused = paused;
  try {
    localStorage.setItem(MOTION_STORAGE_KEY, paused ? 'paused' : 'running');
    storageAvailable = true;
  } catch {
    // Blocked storage: the choice still applies in memory until the page reloads.
    storageAvailable = false;
  }
  notifyLocal();
}
