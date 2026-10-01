/**
 * The brand eye's pause choice. Before sign-in it is a device choice kept in local
 * storage (only the word "paused" or "running"). After sign-in the account's saved
 * reduced-motion preference is the durable choice; a pending or failed save is held
 * in memory for that account only and discarded whenever the signed-in identity
 * changes, so one account's choice never reaches another.
 */
import { create } from 'zustand';

import { readStored } from '@/lib/safeStorage';
import { useAuthStore } from '@/stores/auth';
import { useProfileStore } from '@/stores/profile';

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

function writeLocalPause(paused: boolean): void {
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

// --- Account choice (after sign-in) ----------------------------------------------

export interface SessionMotion {
  owner: string;
  /** What the viewer asked for; a retry saves this again. */
  intent: boolean;
  paused: boolean;
  saving: boolean;
  failed: boolean;
}

interface MotionPauseState {
  session: SessionMotion | null;
}

export const useMotionPauseStore = create<MotionPauseState>()(() => ({ session: null }));

useAuthStore.subscribe((state, previous) => {
  if (state.user?.id !== previous.user?.id) useMotionPauseStore.setState({ session: null });
});

function currentActor(): string | null {
  return useAuthStore.getState().user?.id ?? null;
}

async function saveAccountChoice(owner: string, paused: boolean): Promise<void> {
  useMotionPauseStore.setState({
    session: { owner, intent: paused, paused, saving: true, failed: false },
  });
  const profiles = useProfileStore.getState();
  if (profiles.owner !== owner || profiles.profile === null) await profiles.reload();
  const saved = await useProfileStore.getState().save({ reduced_motion: paused });
  const session = useMotionPauseStore.getState().session;
  // A later choice or a different signed-in account supersedes this result.
  if (currentActor() !== owner || session?.owner !== owner || session.intent !== paused) return;
  if (saved !== null && saved.reduced_motion === paused) {
    useMotionPauseStore.setState({ session: null });
    return;
  }
  // Never claim a save that did not happen; keep the eye still for this session.
  useMotionPauseStore.setState({
    session: { owner, intent: paused, paused: true, saving: false, failed: true },
  });
}

/** Record the viewer's pause choice for the device or the signed-in account. */
export async function chooseMotionPause(paused: boolean): Promise<void> {
  const owner = currentActor();
  if (owner === null) {
    writeLocalPause(paused);
    return;
  }
  // Resuming clears any pre-sign-in pause; pausing never writes the device choice,
  // so the next account on this browser does not inherit it.
  if (!paused && readLocalPause()) writeLocalPause(false);
  const profiles = useProfileStore.getState();
  const saved = profiles.owner === owner ? profiles.profile?.reduced_motion : undefined;
  if (saved === paused) {
    useMotionPauseStore.setState({ session: null });
    return;
  }
  await saveAccountChoice(owner, paused);
}

export async function retryMotionPause(): Promise<void> {
  const owner = currentActor();
  const session = useMotionPauseStore.getState().session;
  if (owner === null || session?.owner !== owner || session.saving) return;
  await saveAccountChoice(owner, session.intent);
}
