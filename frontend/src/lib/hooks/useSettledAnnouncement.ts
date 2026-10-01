import { useCallback, useEffect, useRef, useState } from 'react';

/** How long a user's change must rest (typing, paging) before its result is announced. */
export const SETTLE_MS = 500;

export interface SettledAnnouncement {
  /** Text for a polite live region; empty until the user has asked for a result. */
  text: string;
  /** Changes with every announcement, so a keyed node re-announces an identical result. */
  id: number;
}

/**
 * Announce a result only after the user asked for it, once their change has settled.
 * Background updates to `summary` (streamed records, live counts) never announce on their
 * own: they only change what the next user-requested announcement will say.
 */
export function useSettledAnnouncement(summary: string) {
  const latest = useRef(summary);
  const [request, setRequest] = useState(0);
  const [announcement, setAnnouncement] = useState<SettledAnnouncement>({ text: '', id: 0 });
  useEffect(() => {
    latest.current = summary;
  }, [summary]);
  useEffect(() => {
    if (request === 0) return;
    const timer = setTimeout(() => {
      setAnnouncement((previous) => ({ text: latest.current, id: previous.id + 1 }));
    }, SETTLE_MS);
    return () => clearTimeout(timer);
  }, [request]);
  /** Call from the user's own action: a search, filter or page change. */
  const announce = useCallback(() => setRequest((value) => value + 1), []);
  return { announcement, announce };
}
