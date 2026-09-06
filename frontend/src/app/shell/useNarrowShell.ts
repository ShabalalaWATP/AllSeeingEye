import { useSyncExternalStore } from 'react';

const QUERY = '(max-width: 1023px)';
const read = () => typeof window.matchMedia === 'function' && window.matchMedia(QUERY).matches;
function subscribe(onChange: () => void) {
  if (typeof window.matchMedia !== 'function') return () => undefined;
  const media = window.matchMedia(QUERY);
  media.addEventListener('change', onChange);
  return () => media.removeEventListener('change', onChange);
}

/** Match the desktop rail breakpoint without mounting duplicate navigation. */
export function useNarrowShell() {
  return useSyncExternalStore(subscribe, read, () => false);
}
