import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';

/** A viewport label escapes the rails' scroll clipping and works with keyboard focus. */
export function MapControlLabel({ label, children }: { label: string; children: ReactNode }) {
  const [anchor, setAnchor] = useState<{ x: number; y: number; right: boolean } | null>(null);
  useEffect(() => {
    if (!anchor) return;
    const hide = () => setAnchor(null);
    const key = (event: KeyboardEvent) => {
      if (event.key === 'Escape') hide();
    };
    window.addEventListener('scroll', hide, true);
    window.addEventListener('resize', hide);
    window.addEventListener('keydown', key);
    return () => {
      window.removeEventListener('scroll', hide, true);
      window.removeEventListener('resize', hide);
      window.removeEventListener('keydown', key);
    };
  }, [anchor]);
  const show = (element: HTMLElement) => {
    const bounds = element.getBoundingClientRect();
    const right = bounds.left < window.innerWidth / 2;
    setAnchor({
      x: right ? bounds.right + 8 : bounds.left - 8,
      y: Math.max(20, Math.min(window.innerHeight - 20, bounds.top + bounds.height / 2)),
      right,
    });
  };
  return (
    <span
      role="presentation"
      className="map-labelled-control"
      onMouseEnter={(event) => show(event.currentTarget)}
      onMouseLeave={() => setAnchor(null)}
      onFocus={(event) => show(event.currentTarget)}
      onBlur={() => setAnchor(null)}
    >
      {children}
      {anchor &&
        createPortal(
          <span
            role="tooltip"
            className="map-control-label"
            style={{
              left: anchor.x,
              top: anchor.y,
              transform: `translate(${anchor.right ? '0' : '-100%'}, -50%)`,
            }}
          >
            {label}
          </span>,
          document.body,
        )}
    </span>
  );
}
