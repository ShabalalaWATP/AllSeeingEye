/**
 * A content-free "the bell may have changed" signal. The live stream raises it for a
 * bell change or a new alert; the bell then refetches through its authorised endpoint.
 */
const listeners = new Set<() => void>();

export function subscribeBellChanges(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function signalBellChanged(): void {
  for (const listener of listeners) listener();
}

/** Stream frames that mean the bell should refetch. */
export function isBellFrame(event: string): boolean {
  return event === 'bell.changed' || event === 'alert';
}
