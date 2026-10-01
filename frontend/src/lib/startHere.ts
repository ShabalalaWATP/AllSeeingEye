/**
 * The "Start here" orientation card: its steps, and whether the signed-in account has
 * dismissed it. No server field exists for this, so the choice lives in this browser's
 * storage under a key for the one account id passed in. Nothing here reads another
 * account's key or clears anything else, and following a step only navigates: no step
 * starts collection, research or a model call.
 */
import { readStored, writeStored } from './safeStorage';
import { MAP_GUIDE_PANEL, mapPanelHref } from './mapLayerDirectory';

export interface StartHereStep {
  readonly title: string;
  readonly detail: string;
  readonly to: string;
  readonly linkLabel: string;
}

export const START_HERE_STEPS: readonly StartHereStep[] = [
  {
    title: 'Inspect a map item',
    detail:
      'Open a marker on the map to see its source, time, grade and how precisely it is placed.',
    to: mapPanelHref(MAP_GUIDE_PANEL),
    linkLabel: 'Open the map guide',
  },
  {
    title: 'Ask a research question',
    detail:
      'Write a bounded question, choose its scope and period, and review the draft before you run it.',
    to: '/research',
    linkLabel: 'Go to Research',
  },
  {
    title: 'Set up a subscription',
    detail: 'Run the same research again on a schedule and keep every update as a saved report.',
    to: '/subscriptions',
    linkLabel: 'Go to Subscriptions',
  },
];

const PREFIX = 'ase.start-here.';
const DISMISSED = 'dismissed';
const SHOWN = 'shown';

/** The storage key for one account. Exported for tests; callers pass only their own id. */
export function startHereKey(accountId: string): string {
  return `${PREFIX}${accountId}`;
}

// Keeps the choice for this session when browser storage is blocked.
const memory = new Map<string, string>();
const listeners = new Set<() => void>();

function read(accountId: string): string | null {
  const key = startHereKey(accountId);
  return readStored(key) ?? memory.get(key) ?? null;
}

function write(accountId: string, value: string): void {
  const key = startHereKey(accountId);
  writeStored(key, value);
  if (readStored(key) === value) memory.delete(key);
  else memory.set(key, value);
  for (const listener of listeners) listener();
}

export function subscribeStartHere(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function isStartHereDismissed(accountId: string): boolean {
  return read(accountId) === DISMISSED;
}

export function dismissStartHere(accountId: string): void {
  write(accountId, DISMISSED);
}

/** Show the card again for this account, as Help offers. */
export function reopenStartHere(accountId: string): void {
  write(accountId, SHOWN);
}
