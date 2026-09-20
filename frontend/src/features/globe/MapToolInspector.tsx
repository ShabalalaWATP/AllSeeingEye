import { useRef, useState } from 'react';
import type { CSSProperties, ReactNode, Ref } from 'react';
import { MapControlIcon } from './MapControlIcon';
import type { ControlIcon } from './MapControlIcon';

/** Resizing belongs to the shell, not to individual analysis tools. */
export function MapToolInspector({
  id,
  label,
  title = label,
  icon,
  side = 'right',
  collapsed = false,
  hidden = false,
  closeRef,
  onClose,
  onCollapse,
  children,
  closeLabel = 'Close tool',
  contentKey,
}: {
  id: string;
  label: string;
  title?: string;
  icon: ControlIcon;
  side?: 'left' | 'right';
  collapsed?: boolean;
  hidden?: boolean;
  closeRef?: Ref<HTMLButtonElement>;
  onClose: () => void;
  onCollapse?: () => void;
  children: ReactNode;
  closeLabel?: string;
  contentKey?: string;
}) {
  const [width, setWidth] = useState(360);
  const resize = useRef<{ x: number; width: number } | null>(null);
  const bound = (next: number) => Math.min(600, Math.max(320, next));
  const contentId = `${id}-content`;
  return (
    <section
      id={id}
      aria-label={label}
      className="map-tool-panel"
      data-side={side}
      data-collapsed={collapsed}
      hidden={hidden}
      style={{ '--map-inspector-width': `${width}px` } as CSSProperties}
    >
      {!collapsed && (
        <div
          role="slider"
          tabIndex={0}
          aria-label="Resize tool panel"
          aria-orientation="horizontal"
          aria-valuemin={320}
          aria-valuemax={600}
          aria-valuenow={width}
          aria-controls={id}
          className="map-tool-resizer"
          onKeyDown={(event) => {
            if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
              event.preventDefault();
              setWidth((value) => bound(value + (event.key === 'ArrowRight' ? 24 : -24)));
            } else if (event.key === 'Home' || event.key === 'End') {
              event.preventDefault();
              setWidth(event.key === 'Home' ? 320 : 600);
            }
          }}
          onPointerDown={(event) => {
            if (event.button !== 0) return;
            event.preventDefault();
            resize.current = { x: event.clientX, width };
            event.currentTarget.setPointerCapture(event.pointerId);
          }}
          onPointerMove={(event) => {
            if (!resize.current) return;
            setWidth(
              bound(
                resize.current.width +
                  (event.clientX - resize.current.x) * (side === 'right' ? -1 : 1),
              ),
            );
          }}
          onPointerUp={() => {
            resize.current = null;
          }}
          onPointerCancel={() => {
            resize.current = null;
          }}
          onLostPointerCapture={() => {
            resize.current = null;
          }}
        />
      )}
      <header className="map-tool-heading">
        <span className="map-tool-heading-icon" aria-hidden="true">
          <MapControlIcon name={icon} />
        </span>
        <h2>{title}</h2>
        {onCollapse && (
          <button
            type="button"
            className="map-icon-button"
            onClick={onCollapse}
            aria-label={collapsed ? 'Expand tool' : 'Collapse tool'}
            aria-expanded={!collapsed}
            aria-controls={contentId}
          >
            <svg
              aria-hidden="true"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
            >
              <path d={collapsed ? 'm6 14 6-6 6 6' : 'm6 10 6 6 6-6'} />
            </svg>
          </button>
        )}
        <button
          ref={closeRef}
          type="button"
          aria-label={closeLabel}
          onClick={onClose}
          className="map-icon-button"
        >
          <MapControlIcon name="close" />
        </button>
      </header>
      <div id={contentId} key={contentKey} className="map-tool-content" hidden={collapsed}>
        {children}
      </div>
    </section>
  );
}
