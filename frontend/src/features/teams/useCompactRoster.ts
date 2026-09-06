import { useSyncExternalStore } from 'react';

const QUERY = '(max-width: 639px)';
const read = () => typeof window.matchMedia === 'function' && window.matchMedia(QUERY).matches;
function subscribe(onChange: () => void) {
  if (typeof window.matchMedia !== 'function') return () => undefined;
  const media = window.matchMedia(QUERY);
  media.addEventListener('change', onChange);
  return () => media.removeEventListener('change', onChange);
}

/** Render one semantic roster: a member list on phones, a table on larger screens. */
export function useCompactRoster() {
  return useSyncExternalStore(subscribe, read, () => false);
}
