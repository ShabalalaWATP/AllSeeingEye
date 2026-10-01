import { useCallback, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';

/** Long enough to cross the gap between a rail button and its label (WCAG 1.4.13 hoverable). */
export const TOOLTIP_CLOSE_DELAY_MS = 200;

/**
 * A viewport label escapes the rails' scroll clipping and works with keyboard focus. It stays
 * open while the pointer is over the control or the label, and closes on Escape or blur.
 */
export function MapControlLabel({ label, children }: { label: string; children: ReactNode }) {
  const [anchor, setAnchor] = useState<{ x: number; y: number; right: boolean } | null>(null);
  const closeTimer = useRef<number | null>(null);
  const cancelClose = useCallback(() => {
    if (closeTimer.current !== null) window.clearTimeout(closeTimer.current);
    closeTimer.current = null;
  }, []);
  const hide = useCallback(() => {
    cancelClose();
    setAnchor(null);
  }, [cancelClose]);
  const scheduleClose = () => {
    cancelClose();
    closeTimer.current = window.setTimeout(hide, TOOLTIP_CLOSE_DELAY_MS);
  };
  useEffect(() => cancelClose, [cancelClose]);
  useEffect(() => {
    if (!anchor) return;
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
  }, [anchor, hide]);
  const show = (element: HTMLElement) => {
    cancelClose();
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
      // React delivers enter and leave events through the portal by component tree, so these
      // handlers also cover the label: entering it cancels the close, leaving it schedules one.
      onMouseEnter={(event) => {
        if (event.currentTarget.contains(event.target as Node)) show(event.currentTarget);
        else cancelClose();
      }}
      onMouseLeave={scheduleClose}
      onFocus={(event) => show(event.currentTarget)}
      onBlur={hide}
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
