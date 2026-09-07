import { useSyncExternalStore } from 'react';

const MINUTE = 60_000;
const snapshot = () => Math.floor(Date.now() / MINUTE) * MINUTE;

function subscribe(notify: () => void) {
  let timer: ReturnType<typeof setTimeout>;
  const schedule = () => {
    timer = setTimeout(
      () => {
        notify();
        schedule();
      },
      MINUTE - (Date.now() % MINUTE),
    );
  };
  const visible = () => {
    if (!document.hidden) notify();
  };
  schedule();
  document.addEventListener('visibilitychange', visible);
  return () => {
    clearTimeout(timer);
    document.removeEventListener('visibilitychange', visible);
  };
}

/** Align displayed minutes to the clock boundary, including after tab suspension. */
export function useMinuteClock() {
  return useSyncExternalStore(subscribe, snapshot, snapshot);
}
