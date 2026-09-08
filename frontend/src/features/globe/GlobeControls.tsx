import { Children, isValidElement, useEffect, useId, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { MapControlLabel } from './MapControlLabel';
import { MapControlIcon } from './MapControlIcon';
import type { ControlIcon } from './MapControlIcon';

interface PanelProps {
  label: string;
  icon: ControlIcon;
  side?: 'left' | 'right';
  children: ReactNode;
}
export function ControlPanel({ children }: PanelProps) {
  return children;
}

/** Non-modal tools leave map gestures available, including while measuring. */
export function GlobeControls({
  children,
  layers,
  navigation,
}: {
  children: ReactNode;
  layers: ReactNode;
  navigation?: ReactNode;
}) {
  const [active, setActive] = useState<string | null>(null);
  const id = useId();
  const opener = useRef<HTMLButtonElement | null>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const panels = Children.toArray(children).filter(isValidElement<PanelProps>);
  const selected = panels.find((panel) => panel.props.label === active);
  const close = () => {
    setActive(null);
    opener.current?.focus();
  };
  useEffect(() => {
    if (!active) return;
    closeButton.current?.focus();
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !event.defaultPrevented) {
        setActive(null);
        opener.current?.focus();
      }
    };
    document.addEventListener('keydown', dismiss);
    return () => document.removeEventListener('keydown', dismiss);
  }, [active]);
  const panelButtons = (side: 'left' | 'right') =>
    panels
      .filter((panel) => (panel.props.side ?? 'right') === side)
      .map(({ props }) => (
        <MapControlLabel key={props.label} label={props.label}>
          <button
            type="button"
            className={`map-icon-button ${props.label === 'Map style' ? 'map-style-button' : ''}`}
            aria-label={props.label}
            title={props.label}
            aria-expanded={active === props.label}
            aria-controls={active === props.label ? id : undefined}
            onClick={(event) => {
              opener.current = event.currentTarget;
              setActive(active === props.label ? null : props.label);
            }}
          >
            <MapControlIcon name={props.icon} />
            {props.label === 'Map style' && <span className="map-style-label">Map style</span>}
          </button>
        </MapControlLabel>
      ));
  return (
    <>
      <div className="map-layer-rail" role="group" aria-label="Map layers">
        {panelButtons('left')}
        <div className="map-rail-divider" />
        {layers}
      </div>
      <div className="map-tool-rail" role="group" aria-label="Map tools">
        {panelButtons('right')}
        {navigation}
      </div>
      {selected && (
        <section
          id={id}
          aria-label={active ?? undefined}
          className="map-tool-panel"
          data-side={selected.props.side ?? 'right'}
        >
          <header className="flex items-center justify-between border-b border-line px-3 py-1">
            <h2 className="text-xs font-medium">{active}</h2>
            <button
              ref={closeButton}
              type="button"
              aria-label="Close tool"
              onClick={close}
              className="map-icon-button"
            >
              <MapControlIcon name="close" />
            </button>
          </header>
          <div className="map-tool-content">{selected.props.children}</div>
        </section>
      )}
    </>
  );
}
