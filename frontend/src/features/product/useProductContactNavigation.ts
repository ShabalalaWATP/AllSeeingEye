import { useEffect } from 'react';
import { useLocation } from 'react-router';

/** Router fragment navigation arrives before this lazy, configuration-gated page. */
export function useProductContactNavigation(): void {
  const { hash, key } = useLocation();
  useEffect(() => {
    if (hash !== '#contact') return;
    // Only the advertised contact target is handled; no URL-built selector.
    const section = document.getElementById('contact');
    const heading = section?.querySelector('h2');
    if (section === null || heading === null || heading === undefined) return;
    heading.tabIndex = -1;
    heading.focus({ preventScroll: true });
    section.scrollIntoView({ block: 'start', behavior: 'instant' });
  }, [hash, key]);
}
